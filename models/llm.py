from __future__ import annotations

from langchain_openai import ChatOpenAI

from models.llm_settings import API_KEY, BASE_URL, MODEL_NAME


def build_chat_model(*, temperature: float = 0.1, max_tokens: int | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
    )

