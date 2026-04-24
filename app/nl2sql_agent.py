from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import create_react_agent

from constraint.tool_payload_constraint import ExecuteSQLPayload
from tools.db.tool_schema_store import _load_database_schema_impl
from memory.checkpoint import build_memory
from models.llm import build_chat_model
from prompts.workflow_system_prompt import get_7phase_system_prompt

EXECUTE_SQL_TOOL_NAME = "execute_sql_tool"
GENERATE_DSL_TOOL_NAME = "generate_dsl_tool"


def _coerce_tool_args(args: Any) -> dict:
    """将 LangChain 工具调用参数统一转为 dict（支持 None、dict、JSON 字符串）。"""
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        s = args.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_execute_sql_tool_content(content: Any) -> Optional[ExecuteSQLPayload]:
    """将 execute_sql_tool 的 ToolMessage.content 解析为 dict（与 tools.db.tool_postgres.execute_sql 返回结构一致）。"""
    if content is None:
        return None
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        s = content.strip()
        if not s:
            return None
        try:
            o = json.loads(s)
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            pass
        try:
            import ast

            o = ast.literal_eval(s)
            return o if isinstance(o, dict) else None
        except (ValueError, SyntaxError):
            return None
    return None


def _parse_tool_content(content: Any) -> Any:
    """将 ToolMessage.content 尽量解析为 Python 对象（dict/list/str...）。"""
    if content is None:
        return None
    if isinstance(content, (dict, list, int, float, bool)):
        return content
    if isinstance(content, str):
        s = content.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            import ast

            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            return content
    return content


def extract_last_tool_result_from_messages(messages: list, tool_name: str) -> Any:
    """从 LangGraph ReAct 消息序列中取「最后一次」指定工具的返回内容（尽量解析为 Python 对象）。"""
    pending = set()
    results: list[Any] = []

    for msg in messages:
        for tc in getattr(msg, "tool_calls", None) or []:
            if tc.get("name") != tool_name:
                continue
            tid = tc.get("id") or ""
            pending.add(str(tid))

        if isinstance(msg, ToolMessage):
            name = getattr(msg, "name", None) or ""
            if name and name != tool_name:
                continue
            tid = msg.tool_call_id or ""
            tid_s = str(tid)
            if tid_s not in pending:
                continue
            pending.discard(tid_s)
            results.append(_parse_tool_content(msg.content))

    return results[-1] if results else None


def extract_last_execute_sql_from_messages(
    messages: list,
) -> tuple[Optional[str], Optional[ExecuteSQLPayload]]:
    """从消息序列中取「最后一次」execute_sql_tool 的入参 SQL 与工具返回 dict。"""
    pending_sql_by_id: dict[str, Optional[str]] = {}
    pairs: list[tuple[Optional[str], Optional[ExecuteSQLPayload]]] = []

    for msg in messages:
        for tc in getattr(msg, "tool_calls", None) or []:
            if tc.get("name") != EXECUTE_SQL_TOOL_NAME:
                continue
            tid_s = str(tc.get("id") or "")
            args = _coerce_tool_args(tc.get("args"))
            pending_sql_by_id[tid_s] = args.get("sql")

        if isinstance(msg, ToolMessage):
            name = getattr(msg, "name", None) or ""
            if name and name != EXECUTE_SQL_TOOL_NAME:
                continue
            tid_s = str(msg.tool_call_id or "")
            if tid_s not in pending_sql_by_id:
                continue
            sql = pending_sql_by_id.pop(tid_s)
            parsed = _parse_execute_sql_tool_content(msg.content)
            pairs.append((sql, parsed))

    if not pairs:
        return None, None
    return pairs[-1]


_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_SQL_STMT_RE = re.compile(r"(?is)\b(with\b[\s\S]+?\)\s*)?select\b[\s\S]+?(?:;|\Z)")


def extract_sql_from_text(text: str) -> Optional[str]:
    """从模型最终文本中尽量提取 SQL（与 Gradio 侧历史逻辑一致，供兜底展示）。"""
    if not text:
        return None
    m = _SQL_FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        return candidate or None
    m2 = _SQL_STMT_RE.search(text)
    if m2:
        return m2.group(0).strip()
    return None


def execute_payload_to_dataframe(payload: Optional[ExecuteSQLPayload]) -> tuple[pd.DataFrame, str]:
    """将 execute_sql 工具返回的 payload 转为 DataFrame 与说明文案。"""
    if payload is None:
        return pd.DataFrame(), "Agent 未成功执行 SQL，或未产生可解析的执行结果。"
    if payload.get("status") != "success":
        return pd.DataFrame(), f"Neon 执行失败：{payload.get('msg', payload)}"
    cols = payload.get("columns") or []
    rows = payload.get("rows") or []
    if not cols and not rows:
        return pd.DataFrame(), "查询成功，无返回列/行（可能为 DDL 或非 SELECT）。"
    df = pd.DataFrame(rows, columns=cols)
    total = len(df)
    return df, f"Neon 查询成功，共 {total} 行。"


def _stringify_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        try:
            s = json.dumps(content, ensure_ascii=False)
        except Exception:
            s = str(content)
        return s if len(s) <= 12000 else s[:12000] + "\n...(truncated)"
    return str(content)


def format_messages_for_debug(messages: list, max_tool_chars: int = 6000) -> str:
    """将 LangGraph 消息序列格式化为可读调试日志（System 内容省略长度）。"""
    lines: list[str] = []
    for i, msg in enumerate(messages):
        msg_type = getattr(msg, "type", None) or type(msg).__name__
        if msg_type == "system":
            body = _stringify_message_content(getattr(msg, "content", ""))
            lines.append(f"--- [{i}] system ---\n(omitted, {len(body)} chars)")
            continue
        if msg_type == "human":
            lines.append(f"--- [{i}] human ---\n{_stringify_message_content(getattr(msg, 'content', ''))}")
            continue
        if msg_type == "ai":
            body = _stringify_message_content(getattr(msg, "content", ""))
            tcs = getattr(msg, "tool_calls", None) or []
            lines.append(f"--- [{i}] ai ---\n{body}")
            if tcs:
                try:
                    lines.append("tool_calls:\n" + json.dumps(tcs, ensure_ascii=False, indent=2))
                except Exception:
                    lines.append(f"tool_calls: {tcs}")
            continue
        if msg_type == "tool":
            name = getattr(msg, "name", "") or ""
            c = _stringify_message_content(getattr(msg, "content", ""))
            if len(c) > max_tool_chars:
                c = c[:max_tool_chars] + "\n...(truncated)"
            lines.append(f"--- [{i}] tool:{name} ---\n{c}")
            continue
        lines.append(f"--- [{i}] {msg_type} ---\n{_stringify_message_content(getattr(msg, 'content', ''))}")
    return "\n\n".join(lines)


@dataclass
class AgentGradioResult:
    """供 Gradio 展示：自然语言通路仅通过 Agent，由工具链产生 DSL / SQL / 执行结果。"""

    assistant_text: str
    debug_log: str
    dsl_json: str
    sql: str
    exec_message: str
    result_df: pd.DataFrame


class NL2SQL7PhaseAgent:
    def __init__(self, all_databases):
        """初始化 LLM、七阶段系统提示、工具列表与 LangGraph ReAct Agent（含内存检查点）。"""
        self.llm = build_chat_model(temperature=0.1)
        self.all_databases = all_databases
        self.system_prompt = get_7phase_system_prompt(all_databases)

        self.memory = build_memory()

        from skills.skill_schema import discover_schema_tool
        from skills.skill_schema_sync import sync_local_schema_with_database_tool
        from skills.skill_link import schema_linking_tool
        from skills.skill_decompose import subproblem_decompose_tool
        from skills.skill_plan import query_plan_tool
        from skills.skill_dsl import generate_dsl_tool
        from skills.skill_sql import (
            correct_sql_tool,
            execute_sql_tool,
            generate_sql_from_dsl_tool,
        )

        self.tools = [
            sync_local_schema_with_database_tool,
            discover_schema_tool,
            schema_linking_tool,
            subproblem_decompose_tool,
            query_plan_tool,
            generate_dsl_tool,
            generate_sql_from_dsl_tool,
            execute_sql_tool,
            correct_sql_tool,
        ]

        self.agent = create_react_agent(
            self.llm,
            tools=self.tools,
            checkpointer=self.memory,
        )

    def _invoke(self, user_input: str, thread_id: Optional[str] = None) -> tuple[list, str]:
        # 每次调用前从磁盘重载 schema，避免同进程内 sync 工具已写盘但 system 仍用旧快照
        self.all_databases = _load_database_schema_impl(validate_on_startup=False)
        self.system_prompt = get_7phase_system_prompt(self.all_databases)

        tid = thread_id if thread_id is not None else str(uuid.uuid4())
        config = {"configurable": {"thread_id": tid}}
        state = {
            "messages": [
                ("system", self.system_prompt),
                ("user", f"用户问题：{user_input}"),
            ]
        }
        result = self.agent.invoke(state, config)
        messages = list(result.get("messages") or [])
        last = messages[-1] if messages else None
        assistant_text = ""
        if last is not None:
            c = getattr(last, "content", "") or ""
            assistant_text = c if isinstance(c, str) else str(c)
        return messages, assistant_text

    def run(self, user_input, thread_id: Optional[str] = None) -> str:
        _, assistant_text = self._invoke(user_input, thread_id=thread_id)
        return assistant_text

    def run_for_gradio(self, user_input: str, thread_id: Optional[str] = None) -> AgentGradioResult:
        """运行 ReAct Agent，并整理 Gradio 所需字段（执行结果来自工具返回）。"""
        messages, assistant_text = self._invoke(user_input, thread_id=thread_id)

        last_sql, exec_payload = extract_last_execute_sql_from_messages(messages)
        sql = (last_sql or "").strip() if last_sql else ""
        if not sql:
            extracted = extract_sql_from_text(assistant_text)
            sql = (extracted or "").strip()

        dsl_raw = extract_last_tool_result_from_messages(messages, GENERATE_DSL_TOOL_NAME)
        if isinstance(dsl_raw, dict):
            dsl_json = json.dumps(dsl_raw, ensure_ascii=False, indent=2)
        elif dsl_raw is not None:
            dsl_json = str(dsl_raw)
        else:
            dsl_json = ""

        result_df, exec_message = execute_payload_to_dataframe(exec_payload)
        debug_log = format_messages_for_debug(messages)
        if assistant_text:
            debug_log += "\n\n=== 最终回复 ===\n" + assistant_text

        return AgentGradioResult(
            assistant_text=assistant_text,
            debug_log=debug_log,
            dsl_json=dsl_json,
            sql=sql,
            exec_message=exec_message,
            result_df=result_df,
        )

