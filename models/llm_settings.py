from __future__ import annotations

from models.env import env


# LLM 配置（从环境变量 / .env 读取）
API_KEY = env("NL2SQL_API_KEY", "") or ""
BASE_URL = env("NL2SQL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1") or ""
MODEL_NAME = env("NL2SQL_MODEL_NAME", "qwen3-coder-480b-a35b-instruct") or ""

