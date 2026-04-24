# Gradio UI 与回调（含 schema 校验/更新交互；查询通路仅通过 LangGraph Agent）
import socket
import sys
import time
from decimal import Decimal
from typing import List, Optional, Tuple

import gradio as gr
import pandas as pd

from app.nl2sql_agent import NL2SQL7PhaseAgent
from tools.db.tool_schema_store import (
    _check_latest_schema_once_impl,
    _load_database_schema_impl,
    _refresh_local_schema_file_impl,
)
from prompts.user_query_prompt import build_user_query as build_user_query_prompt

# Agent 输出区域可滚动（内容超出时在框内下拉滚动）
SCROLL_CSS = """
.agent-output-scroll textarea {
    max-height: min(70vh, 520px) !important;
    overflow-y: auto !important;
    resize: vertical !important;
}
"""

NEON_RESULT_MAX_ROWS = 500


_PLOT_TYPES = [
    "直方图（单数值列）",
    "柱状图（维度 + 数值汇总）",
    "折线图（趋势：x + y）",
    "散点图（x + y）",
    "箱线图（维度 + 数值分布）",
]


def _is_numeric_series(s: pd.Series) -> bool:
    try:
        return pd.api.types.is_numeric_dtype(s)
    except Exception:
        return False


def _is_datetime_series(s: pd.Series) -> bool:
    try:
        return pd.api.types.is_datetime64_any_dtype(s)
    except Exception:
        return False


def _coerce_datetime_series(s: pd.Series) -> pd.Series:
    if _is_datetime_series(s):
        return s
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return s


def _df_columns(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty:
        return []
    return [str(c) for c in df.columns]


def _safe_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    dff = df.copy()
    dff.columns = [str(c) for c in dff.columns]
    return dff


def describe_one_column(df: pd.DataFrame, col: str) -> str:
    dff = _safe_df(df)
    if dff.empty:
        return "结果为空。"
    if not col or col not in dff.columns:
        return "请选择一列查看描述性统计。"

    s = dff[col]
    missing = int(s.isna().sum())
    total = int(len(s))
    unique = int(s.nunique(dropna=True))

    lines = [
        f"**列名**：`{col}`",
        f"- 总行数：**{total}**",
        f"- 缺失值：**{missing}**",
        f"- 去重值数量：**{unique}**",
    ]

    if _is_numeric_series(s):
        desc = s.describe()
        lines.append("")
        lines.append("**数值列统计**")
        try:
            lines.append(desc.to_frame(name=col).to_markdown())
        except Exception:
            lines.append("```")
            lines.append(desc.to_string())
            lines.append("```")
    else:
        top = s.astype(str).value_counts(dropna=True).head(20)
        lines.append("")
        lines.append("**Top20 频次（非数值列）**")
        try:
            lines.append(top.to_frame(name="count").to_markdown())
        except Exception:
            lines.append("```")
            lines.append(top.to_string())
            lines.append("```")

    return "\n".join(lines)


def _validate_plot_request(
    df: pd.DataFrame,
    plot_type: str,
    x_col: Optional[str],
    y_col: Optional[str],
    group_col: Optional[str],
) -> Tuple[bool, str]:
    dff = _safe_df(df)
    if dff.empty:
        return False, "结果为空，无法绘图。"
    if plot_type not in _PLOT_TYPES:
        return False, "请选择绘图类型。"

    def col_exists(c: Optional[str]) -> bool:
        return bool(c) and str(c) in dff.columns

    if plot_type == "直方图（单数值列）":
        if not col_exists(x_col):
            return False, "建议：选择 **1 个数值列** 作为直方图的列。"
        if not _is_numeric_series(dff[str(x_col)]):
            return False, "不适合：直方图需要 **数值列**。建议改选数值列，或改用“柱状图/箱线图”。"
        return True, "适合：将绘制该数值列的分布直方图。"

    if plot_type == "散点图（x + y）":
        if not (col_exists(x_col) and col_exists(y_col)):
            return False, "建议：散点图需要选择 **x、y 两列**。"
        x, y = str(x_col), str(y_col)
        if not _is_numeric_series(dff[x]) or not _is_numeric_series(dff[y]):
            return False, "不适合：散点图通常需要 **x、y 都是数值列**。建议改选数值列，或改用“柱状图/折线图”。"
        return True, "适合：将绘制数值列之间的散点关系。"

    if plot_type == "折线图（趋势：x + y）":
        if not (col_exists(x_col) and col_exists(y_col)):
            return False, "建议：折线图需要选择 **x（时间/有序）** 和 **y（数值）**。"
        x, y = str(x_col), str(y_col)
        y_ok = _is_numeric_series(dff[y])
        x_dt = _coerce_datetime_series(dff[x])
        x_ok = _is_datetime_series(x_dt) or _is_numeric_series(dff[x])
        if not y_ok:
            return False, "不适合：折线图的 y 需要是 **数值列**。建议改选数值列作为 y。"
        if not x_ok:
            return False, "不适合：折线图的 x 建议为 **日期/数值（有序）**。建议改选日期列（或可排序的数值列）。"
        return True, "适合：将绘制趋势折线图。"

    if plot_type in ("柱状图（维度 + 数值汇总）", "箱线图（维度 + 数值分布）"):
        if not (col_exists(x_col) and col_exists(y_col)):
            return False, "建议：选择 **维度列（x）** + **数值列（y）**。"
        x, y = str(x_col), str(y_col)
        if _is_numeric_series(dff[x]):
            return False, "不适合：维度列（x）不建议是数值列。建议把 x 换成类别/字符串列。"
        if not _is_numeric_series(dff[y]):
            return False, "不适合：y 需要是 **数值列**。建议把 y 换成数值列。"
        if group_col and str(group_col) in dff.columns and str(group_col) == x:
            return False, "建议：分组列不需要与 x 重复，可留空或换另一列。"
        return True, "适合：将按维度列展示数值列（柱状汇总/箱线分布）。"

    return False, "该绘图类型暂未支持。"


def render_plot(
    df: pd.DataFrame,
    plot_type: str,
    x_col: Optional[str],
    y_col: Optional[str],
    group_col: Optional[str],
) -> Tuple[object, str]:
    ok, msg = _validate_plot_request(df, plot_type, x_col, y_col, group_col)
    if not ok:
        return None, msg

    dff = _safe_df(df)
    x = str(x_col) if x_col else ""
    y = str(y_col) if y_col else ""
    g = str(group_col) if group_col else ""

    try:
        import plotly.express as px  # type: ignore
    except Exception:
        px = None  # type: ignore

    if px is not None:
        if plot_type == "直方图（单数值列）":
            fig = px.histogram(dff, x=x, nbins=30, title=f"直方图：{x}")
            return fig, "已生成图表（Plotly）。"
        if plot_type == "散点图（x + y）":
            fig = px.scatter(dff, x=x, y=y, color=g if g else None, title=f"散点图：{y} vs {x}")
            return fig, "已生成图表（Plotly）。"
        if plot_type == "折线图（趋势：x + y）":
            dd = dff.copy()
            dd[x] = _coerce_datetime_series(dd[x])
            try:
                dd = dd.sort_values(x)
            except Exception:
                pass
            fig = px.line(dd, x=x, y=y, color=g if g else None, title=f"折线图：{y} over {x}")
            return fig, "已生成图表（Plotly）。"
        if plot_type == "柱状图（维度 + 数值汇总）":
            top = (
                dff[[x, y]]
                .dropna(subset=[x, y])
                .groupby(x, as_index=False)[y]
                .sum()
                .sort_values(y, ascending=False)
                .head(20)
            )
            fig = px.bar(top, x=x, y=y, title=f"柱状图（Top20，sum）：{y} by {x}")
            return fig, "已生成图表（Plotly）。"
        if plot_type == "箱线图（维度 + 数值分布）":
            fig = px.box(dff, x=x, y=y, color=g if g else None, title=f"箱线图：{y} by {x}")
            return fig, "已生成图表（Plotly）。"

    fig, m = _try_make_matplotlib_fig(dff)
    return fig, f"Plotly 不可用，已回退 Matplotlib。{m}"


def init_viz_panel(df: pd.DataFrame):
    cols = _df_columns(df)
    dff = _safe_df(df)
    numeric_cols = list(dff.select_dtypes(include="number").columns) if not dff.empty else []
    first_col = cols[0] if cols else None
    first_num = str(numeric_cols[0]) if numeric_cols else first_col

    stats_md = describe_one_column(dff, first_col) if first_col else "结果为空。"
    plot_fig, plot_msg = (None, "请选择绘图参数后点击“生成图表”。")
    return (
        gr.update(choices=cols, value=first_col),
        stats_md,
        gr.update(choices=_PLOT_TYPES, value=_PLOT_TYPES[0]),
        gr.update(choices=cols, value=first_num),
        gr.update(choices=cols, value=None),
        gr.update(choices=[""] + cols, value=""),
        plot_fig,
        plot_msg,
    )


def _try_make_plotly_fig(df: pd.DataFrame):
    try:
        import plotly.express as px  # type: ignore
    except Exception:
        return None, "Plotly 不可用，已回退到 Matplotlib。"

    if df is None or df.empty:
        return None, "结果为空，无可视化。"

    dff = df.copy()
    dff.columns = [str(c) for c in dff.columns]

    numeric_cols = list(dff.select_dtypes(include="number").columns)
    other_cols = [c for c in dff.columns if c not in numeric_cols]

    if len(numeric_cols) >= 2:
        x, y = numeric_cols[0], numeric_cols[1]
        fig1 = px.scatter(dff, x=x, y=y, title=f"散点图：{y} vs {x}")
    elif len(numeric_cols) == 1:
        x = numeric_cols[0]
        fig1 = px.histogram(dff, x=x, nbins=30, title=f"分布直方图：{x}")
    else:
        fig1 = None

    fig2 = None
    if other_cols and numeric_cols:
        dim = other_cols[0]
        val = numeric_cols[0]
        top = (
            dff[[dim, val]]
            .dropna(subset=[dim, val])
            .groupby(dim, as_index=False)[val]
            .sum()
            .sort_values(val, ascending=False)
            .head(20)
        )
        if not top.empty:
            fig2 = px.bar(top, x=dim, y=val, title=f"Top20：按 {dim} 汇总 {val}(sum)")

    if fig1 is None and fig2 is None:
        return None, "未识别到可用于绘图的列（缺少数值列）。"

    if fig1 is not None and fig2 is not None:
        from plotly.subplots import make_subplots  # type: ignore

        combo = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=(fig1.layout.title.text or "", fig2.layout.title.text or ""),
        )
        for tr in fig1.data:
            combo.add_trace(tr, row=1, col=1)
        for tr in fig2.data:
            combo.add_trace(tr, row=1, col=2)
        combo.update_layout(height=420, showlegend=False, title_text="可视化分析")
        return combo, "已生成可视化（Plotly）。"

    return (fig1 or fig2), "已生成可视化（Plotly）。"


def _try_make_matplotlib_fig(df: pd.DataFrame):
    try:
        import matplotlib

        matplotlib.use("Agg")
        _configure_matplotlib_for_chinese(matplotlib)
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        return None, f"Matplotlib 不可用，无法生成图表：{e}"

    if df is None or df.empty:
        return None, "结果为空，无可视化。"

    dff = df.copy()
    dff.columns = [str(c) for c in dff.columns]
    numeric_cols = list(dff.select_dtypes(include="number").columns)
    other_cols = [c for c in dff.columns if c not in numeric_cols]

    fig, ax = plt.subplots(figsize=(10, 4))
    if len(numeric_cols) >= 2:
        x, y = numeric_cols[0], numeric_cols[1]
        ax.scatter(dff[x], dff[y], s=10, alpha=0.7)
        ax.set_title(f"散点图：{y} vs {x}")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
    elif len(numeric_cols) == 1:
        x = numeric_cols[0]
        ax.hist(dff[x].dropna(), bins=30)
        ax.set_title(f"分布直方图：{x}")
        ax.set_xlabel(x)
        ax.set_ylabel("count")
    elif other_cols:
        dim = other_cols[0]
        vc = dff[dim].astype(str).value_counts().head(20)
        vc.iloc[::-1].plot(kind="barh", ax=ax)
        ax.set_title(f"Top20 频次：{dim}")
        ax.set_xlabel("count")
    else:
        plt.close(fig)
        return None, "未识别到可用于绘图的列。"

    fig.tight_layout()
    return fig, "已生成可视化（Matplotlib）。"


def _configure_matplotlib_for_chinese(matplotlib_module) -> None:
    try:
        from matplotlib import font_manager  # type: ignore

        installed = {f.name for f in font_manager.fontManager.ttflist}
        preferred = [
            "Microsoft YaHei",
            "微软雅黑",
            "SimHei",
            "黑体",
            "SimSun",
            "宋体",
            "PingFang SC",
            "Noto Sans CJK SC",
            "Source Han Sans SC",
        ]
        candidates = [n for n in preferred if n in installed]
        if candidates:
            matplotlib_module.rcParams["font.sans-serif"] = candidates
        matplotlib_module.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def simple_df_profile(df: pd.DataFrame) -> Tuple[str, object, str]:
    if df is None or df.empty:
        return "结果为空，无可分析数据。", None, "无图表。"

    dff = df.copy()
    dff.columns = [str(c) for c in dff.columns]

    rows, cols = dff.shape
    missing = int(dff.isna().sum().sum())
    numeric_cols = list(dff.select_dtypes(include="number").columns)
    text_cols = [c for c in dff.columns if c not in numeric_cols]

    summary_lines = [
        f"- 行数：**{rows}**",
        f"- 列数：**{cols}**",
        f"- 缺失值总数：**{missing}**",
        f"- 数值列：**{len(numeric_cols)}**",
        f"- 非数值列：**{len(text_cols)}**",
    ]

    if numeric_cols:
        desc = dff[numeric_cols].describe().transpose()
        desc = desc.round(6)
        desc_show = desc.head(12)
        summary_lines.append("")
        summary_lines.append("**数值列描述统计（最多展示前 12 列）**")
        try:
            summary_lines.append(desc_show.to_markdown())
        except Exception:
            summary_lines.append("```")
            summary_lines.append(desc_show.to_string())
            summary_lines.append("```")

    md = "\n".join(summary_lines)

    fig, fig_msg = _try_make_plotly_fig(dff)
    if fig is None:
        fig, fig_msg2 = _try_make_matplotlib_fig(dff)
        fig_msg = f"{fig_msg} {fig_msg2}".strip()

    return md, fig, fig_msg


def build_user_query(biz_need: str, stat_dim: str) -> str:
    biz_need = (biz_need or "").strip()
    stat_dim = (stat_dim or "").strip()
    if not biz_need:
        raise ValueError("业务需求不能为空")
    return build_user_query_prompt(biz_need, stat_dim)


def format_df_for_report(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    dff = df.copy()
    dff.columns = [str(c) for c in dff.columns]

    new_cols = []
    for i in range(dff.shape[1]):
        s = dff.iloc[:, i].copy()
        if s.dtype == "object" or pd.api.types.is_string_dtype(s):
            try:
                s = s.map(lambda v: float(v) if isinstance(v, Decimal) else v)
            except Exception:
                pass

        try:
            if s.dtype == "object" or pd.api.types.is_string_dtype(s):
                ss = s.astype(str).str.strip()
                ss = ss.str.replace(",", "", regex=False)
                ss = ss.str.replace("%", "", regex=False)
                ss = ss.replace({"": None, "None": None, "nan": None, "NaN": None})
                numeric = pd.to_numeric(ss, errors="coerce")

                non_null = int(pd.notna(s).sum())
                converted = int(pd.notna(numeric).sum())
                if non_null > 0 and converted / non_null >= 0.8:
                    s = numeric
            else:
                s = pd.to_numeric(s, errors="ignore")
        except Exception:
            pass

        if pd.api.types.is_float_dtype(s):
            try:
                s = s.round(6)
            except Exception:
                pass

        new_cols.append(s)

    out = pd.concat(new_cols, axis=1)
    out.columns = list(dff.columns)
    return out


ALL_DB = None
AGENT = None


def _get_db_and_agent():
    global ALL_DB, AGENT
    if ALL_DB is None:
        ALL_DB = _load_database_schema_impl()
    if AGENT is None:
        AGENT = NL2SQL7PhaseAgent(ALL_DB)
    return ALL_DB, AGENT


def run_nl2sql(
    biz_need: str,
    stat_dim: str,
    progress=gr.Progress(track_tqdm=False),
) -> Tuple[str, str, str, str, str, str, pd.DataFrame, pd.DataFrame]:
    t0 = time.perf_counter()
    phase_ms: dict[str, float] = {}

    def _set_progress(pct: float, desc: str) -> None:
        try:
            if progress is not None:
                progress(pct, desc=desc)
        except Exception:
            pass

    def _timeit(label: str):
        class _Timer:
            def __enter__(self_inner):
                self_inner._start = time.perf_counter()
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                phase_ms[label] = phase_ms.get(label, 0.0) + (time.perf_counter() - self_inner._start) * 1000.0
                return False

        return _Timer()

    _set_progress(0.05, "解析输入")
    user_query = build_user_query(biz_need, stat_dim)

    _set_progress(0.12, "加载 Schema 与 Agent")
    with _timeit("初始化（Schema + Agent）"):
        _, agent = _get_db_and_agent()

    _set_progress(0.22, "Agent 推理与工具调用（LangGraph）")
    with _timeit("Agent（ReAct + tools）"):
        gr_result = agent.run_for_gradio(user_query)

    raw_row_count = len(gr_result.result_df) if gr_result.result_df is not None else 0
    neon_df = format_df_for_report(gr_result.result_df)
    neon_msg = gr_result.exec_message
    if raw_row_count > NEON_RESULT_MAX_ROWS and neon_msg.startswith("Neon 查询成功"):
        neon_df = neon_df.head(NEON_RESULT_MAX_ROWS).copy()
        neon_msg = f"Neon 查询成功，共 {raw_row_count} 行（界面仅展示前 {NEON_RESULT_MAX_ROWS} 行）。"

    dsl_str = gr_result.dsl_json or ""
    sql = gr_result.sql or ""
    verbose_log = gr_result.debug_log or ""

    total_ms = max((time.perf_counter() - t0) * 1000.0, 0.001)
    items = sorted(phase_ms.items(), key=lambda kv: kv[1], reverse=True)
    timing_lines = ["=== 耗时统计（本次运行）===", f"- 总耗时：{total_ms:.1f} ms"]
    for k, v in items:
        timing_lines.append(f"- {k}: {v:.1f} ms ({v / total_ms * 100:.1f}%)")
    timing_report = "\n".join(timing_lines)

    _set_progress(1.0, "完成")
    return user_query, timing_report, verbose_log, dsl_str, sql, neon_msg, neon_df, neon_df


demo = gr.Blocks(title="银行风控 NL2SQL 即席查询")
with demo:
    gr.Markdown("## 银行风控 NL2SQL 即席查询")
    gr.Markdown("在浏览器里输入业务需求和统计维度，生成 PostgreSQL SQL 并展示查询结果。")

    schema_ok_state = gr.State(True)
    schema_msg = gr.Markdown(visible=False)
    schema_refresh_btn = gr.Button("更新本地 Schema（将覆盖项目根目录 database_schema.json）", variant="secondary", visible=False)

    with gr.Row():
        biz_need = gr.Textbox(
            label="业务需求",
            placeholder="例如：统计各产品的贷款笔数、贷款金额、逾期率（必填）",
            lines=3,
        )
        stat_dim = gr.Textbox(
            label="统计维度（可选）",
            placeholder="例如：产品编码、贷款状态（非必填）",
            lines=3,
        )

    run_btn = gr.Button("运行", variant="primary")

    with gr.Row():
        with gr.Column(scale=7):
            with gr.Tabs():
                with gr.TabItem("PostgreSQL 语句"):
                    out_sql = gr.Code(label="sql", language="sql")
                with gr.TabItem("Neon 数据库查询结果"):
                    df_state = gr.State(pd.DataFrame())
                    neon_status = gr.Textbox(label="执行说明", lines=2, interactive=False)
                    neon_table = gr.Dataframe(
                        label="查询结果（PostgreSQL / Neon）",
                        wrap=True,
                        interactive=False,
                    )
                    with gr.Accordion("简易数据可视化分析", open=True):
                        with gr.Row():
                            stats_col = gr.Dropdown(label="选择一列查看描述性统计", choices=[], value=None)

                        stats_md = gr.Markdown()

                        with gr.Row():
                            plot_type = gr.Dropdown(label="绘图类型", choices=_PLOT_TYPES, value=_PLOT_TYPES[0])
                            x_col = gr.Dropdown(label="x 列", choices=[], value=None)
                            y_col = gr.Dropdown(label="y 列（部分图需要）", choices=[], value=None)
                            group_col = gr.Dropdown(label="分组列（可选）", choices=[""], value="")

                        plot_btn = gr.Button("生成图表", variant="secondary")
                        plot_out = gr.Plot(label="图表输出")
                        plot_status = gr.Textbox(label="建议/说明", lines=3, interactive=False)

        with gr.Column(scale=3, min_width=360):
            gr.Markdown("### 侧边调试面板")
            side_timing = gr.Textbox(
                label="耗时统计/进度",
                lines=8,
                elem_classes=["agent-output-scroll"],
                interactive=False,
            )
            btn_prompt = gr.Button("Prompt 解析", variant="secondary")
            btn_log = gr.Button("运行日志", variant="secondary")
            btn_dsl = gr.Button("DSL（SQL 前）", variant="secondary")

            side_prompt = gr.Textbox(
                label="Prompt 解析",
                lines=26,
                elem_classes=["agent-output-scroll"],
                visible=False,
            )
            side_log = gr.Textbox(
                label="运行日志",
                lines=26,
                elem_classes=["agent-output-scroll"],
                visible=False,
            )
            side_dsl = gr.Textbox(
                label="DSL（SQL 前）",
                lines=26,
                elem_classes=["agent-output-scroll"],
                visible=False,
            )

    run_evt = run_btn.click(
        fn=run_nl2sql,
        inputs=[biz_need, stat_dim],
        outputs=[side_prompt, side_timing, side_log, side_dsl, out_sql, neon_status, neon_table, df_state],
    )

    run_evt.then(
        fn=init_viz_panel,
        inputs=[df_state],
        outputs=[stats_col, stats_md, plot_type, x_col, y_col, group_col, plot_out, plot_status],
    )

    stats_col.change(fn=describe_one_column, inputs=[df_state, stats_col], outputs=[stats_md])

    plot_btn.click(
        fn=render_plot,
        inputs=[df_state, plot_type, x_col, y_col, group_col],
        outputs=[plot_out, plot_status],
    )

    def _show_only(which: str):
        return (
            gr.update(visible=(which == "prompt")),
            gr.update(visible=(which == "log")),
            gr.update(visible=(which == "dsl")),
        )

    btn_prompt.click(fn=lambda: _show_only("prompt"), inputs=[], outputs=[side_prompt, side_log, side_dsl])
    btn_log.click(fn=lambda: _show_only("log"), inputs=[], outputs=[side_prompt, side_log, side_dsl])
    btn_dsl.click(fn=lambda: _show_only("dsl"), inputs=[], outputs=[side_prompt, side_log, side_dsl])

    def _schema_check_on_load():
        res = _check_latest_schema_once_impl()
        if res.ok:
            return (
                True,
                gr.update(visible=False, value=""),
                gr.update(visible=False),
                gr.update(interactive=True),
            )
        text = "\n".join(
            [
                "### Schema 不一致：需要更新本地缓存后才能继续",
                "",
                "下面是差异摘要（来自启动时自动校验）：",
                "",
                f"```text\n{res.message}\n```",
            ]
        )
        return (
            False,
            gr.update(visible=True, value=text),
            gr.update(visible=True),
            gr.update(interactive=False),
        )

    def _schema_refresh_click():
        res = _refresh_local_schema_file_impl()
        if res.ok:
            return (
                True,
                gr.update(visible=False, value=""),
                gr.update(visible=False),
                gr.update(interactive=True),
            )
        text = "\n".join(
            [
                "### Schema 更新失败或仍不一致",
                "",
                f"```text\n{res.message}\n```",
            ]
        )
        return (
            False,
            gr.update(visible=True, value=text),
            gr.update(visible=True),
            gr.update(interactive=False),
        )

    demo.load(
        fn=_schema_check_on_load,
        inputs=[],
        outputs=[schema_ok_state, schema_msg, schema_refresh_btn, run_btn],
    )
    schema_refresh_btn.click(
        fn=_schema_refresh_click,
        inputs=[],
        outputs=[schema_ok_state, schema_msg, schema_refresh_btn, run_btn],
    )


def find_free_port(host: str, preferred: int, max_tries: int = 30) -> int:
    for port in range(preferred, preferred + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"Cannot find empty port in range: {preferred}-{preferred + max_tries - 1}")


def main() -> None:
    _ensure_utf8_stdio()
    host = "127.0.0.1"
    port = find_free_port(host, preferred=7860, max_tries=30)
    demo.queue()
    demo.launch(server_name=host, server_port=port, pwa=True, css=SCROLL_CSS)


if __name__ == "__main__":
    main()

