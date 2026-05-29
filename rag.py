from __future__ import annotations

import logging
import time
from pathlib import Path

from openai import OpenAI

from config import get_settings

# Each item: {"role": "user"|"assistant", "content": str}
Message = dict[str, str]

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.txt"
_instructions: str | None = None

_client: OpenAI | None = None
_vector_store_id: str | None = None


def _get_instructions() -> str:
    global _instructions
    if _instructions is None:
        _instructions = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
        if not _instructions:
            raise RuntimeError(f"System prompt file is empty: {_SYSTEM_PROMPT_PATH}")
    return _instructions


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(
            api_key=settings.yandex_api_key,
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            project=settings.yandex_folder,
        )
    return _client


def _get_vector_store_id() -> str | None:
    global _vector_store_id
    if _vector_store_id is None:
        _vector_store_id = get_settings().yandex_vector_store_id
    return _vector_store_id


def ensure_vector_store() -> str:
    global _vector_store_id
    store_id = _get_vector_store_id()
    if store_id:
        return store_id

    logger.warning(
        "vector store not configured, creating from FAQ",
        extra={"event": "vector_store_bootstrap"},
    )
    client = _get_client()
    file_names = ["documents/FAQ.md"]
    file_ids = []
    for file_name in file_names:
        with open(file_name, "rb") as f:
            uploaded = client.files.create(file=f, purpose="assistants")
        logger.info(
            "faq file uploaded",
            extra={"event": "faq_uploaded", "file": file_name, "file_id": uploaded.id},
        )
        file_ids.append(uploaded.id)

    store = client.vector_stores.create(
        name="digital pm knowledge base",
        file_ids=file_ids,
    )
    _vector_store_id = store.id

    while True:
        store = client.vector_stores.retrieve(_vector_store_id)
        logger.info(
            "vector store indexing",
            extra={"event": "vector_store_status", "status": store.status},
        )
        if store.status == "completed":
            logger.info(
                "vector store ready; set YANDEX_VECTOR_STORE_ID in environment",
                extra={"event": "vector_store_ready", "vector_store_id": _vector_store_id},
            )
            break

    return _vector_store_id


def extract_text(response) -> str:
    output = response.output
    if isinstance(output, str):
        return output

    parts = []
    for item in output or []:
        content = getattr(item, "content", None) or (
            item.get("content") if isinstance(item, dict) else None
        )
        if not content:
            text = getattr(item, "text", None) or (
                item.get("text") if isinstance(item, dict) else None
            )
            if text:
                parts.append(text)
            continue
        for block in content:
            text = getattr(block, "text", None) or (
                block.get("text") if isinstance(block, dict) else None
            )
            if text:
                parts.append(text)

    return "\n".join(parts) if parts else str(output)


def strip_markdown_bold(text: str) -> str:
    """Remove ** markers so Telegram shows plain text, not raw markdown."""
    return text.replace("**", "")


def ask(
    user_input: str,
    *,
    history: list[Message] | None = None,
    chat_id: int | None = None,
) -> str:
    """Send a question to the RAG model and return the answer text.

    Pass `history` for multi-turn dialogue within a session. The list must include
    the latest user message.
    """
    settings = get_settings()
    store_id = ensure_vector_store()
    client = _get_client()

    if history is not None:
        api_input: list[Message] = history
        history_len = len(history)
    else:
        api_input = [{"role": "user", "content": user_input}]
        history_len = 1

    started = time.perf_counter()
    try:
        response = client.responses.create(
            model=settings.yandex_model,
            instructions=_get_instructions(),
            tools=[{"type": "retrieval", "vector_store_id": store_id}],
            input=api_input,
            temperature=0.4,
            max_output_tokens=1000,
        )
    except Exception:
        logger.exception(
            "yandex api request failed",
            extra={
                "event": "rag_request_failed",
                "chat_id": chat_id,
                "history_messages": history_len,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "yandex api request completed",
        extra={
            "event": "rag_request_ok",
            "chat_id": chat_id,
            "history_messages": history_len,
            "duration_ms": duration_ms,
            "response_id": response.id,
        },
    )
    return strip_markdown_bold(extract_text(response))
