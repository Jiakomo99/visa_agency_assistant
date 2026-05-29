from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from config import get_settings

logger = logging.getLogger(__name__)

Message = dict[str, str]

MAX_MESSAGES = 20


@dataclass
class _ChatSession:
    messages: list[Message] = field(default_factory=list)
    last_activity: float = field(default_factory=time.monotonic)


_sessions: dict[int, _ChatSession] = {}


def _ttl_seconds() -> int:
    minutes = get_settings().session_ttl_minutes
    return max(1, minutes) * 60


def _is_expired(session: _ChatSession) -> bool:
    return (time.monotonic() - session.last_activity) > _ttl_seconds()


def _trim(messages: list[Message]) -> None:
    if len(messages) > MAX_MESSAGES:
        del messages[: len(messages) - MAX_MESSAGES]


def clear_session(chat_id: int) -> None:
    if chat_id in _sessions:
        del _sessions[chat_id]
    logger.info(
        "session cleared",
        extra={"event": "session_cleared", "chat_id": chat_id},
    )


def _get_or_create(chat_id: int) -> _ChatSession:
    session = _sessions.get(chat_id)
    if session is None:
        session = _ChatSession()
        _sessions[chat_id] = session
        return session

    if _is_expired(session):
        logger.info(
            "session expired",
            extra={"event": "session_expired", "chat_id": chat_id},
        )
        session.messages.clear()

    session.last_activity = time.monotonic()
    return session


def add_user_message(chat_id: int, content: str) -> list[Message]:
    """Start a turn: ensure session is active, append user message, return full history."""
    session = _get_or_create(chat_id)
    session.messages.append({"role": "user", "content": content})
    _trim(session.messages)
    return list(session.messages)


def add_assistant_message(chat_id: int, content: str) -> None:
    session = _get_or_create(chat_id)
    session.messages.append({"role": "assistant", "content": content})
    _trim(session.messages)


def rollback_last_user_message(chat_id: int) -> None:
    session = _sessions.get(chat_id)
    if not session or not session.messages:
        return
    if session.messages[-1]["role"] == "user":
        session.messages.pop()
