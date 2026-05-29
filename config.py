from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = (
    "TELEGRAM_API_KEY",
    "YANDEX_CLOUD_API_KEY",
    "YANDEX_CLOUD_FOLDER",
    "YANDEX_CLOUD_MODEL",
)


@dataclass(frozen=True)
class Settings:
    telegram_api_key: str
    yandex_api_key: str
    yandex_folder: str
    yandex_model: str
    yandex_vector_store_id: str | None
    log_level: str
    log_json: bool


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def load_settings() -> Settings:
    missing = [name for name in REQUIRED_VARS if not (os.getenv(name) or "").strip()]
    if missing:
        raise ConfigError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in the values."
        )

    log_level = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    log_json_raw = (os.getenv("LOG_JSON") or "true").strip().lower()
    log_json = log_json_raw in ("1", "true", "yes", "on")

    return Settings(
        telegram_api_key=_require("TELEGRAM_API_KEY"),
        yandex_api_key=_require("YANDEX_CLOUD_API_KEY"),
        yandex_folder=_require("YANDEX_CLOUD_FOLDER"),
        yandex_model=_require("YANDEX_CLOUD_MODEL"),
        yandex_vector_store_id=(os.getenv("YANDEX_VECTOR_STORE_ID") or "").strip() or None,
        log_level=log_level,
        log_json=log_json,
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def validate_settings() -> Settings:
    """Load settings and exit the process if configuration is invalid."""
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not settings.yandex_vector_store_id:
        print(
            "Warning: YANDEX_VECTOR_STORE_ID is not set. "
            "The bot may upload FAQ and create a store on first request.",
            file=sys.stderr,
        )

    global _settings
    _settings = settings
    return settings
