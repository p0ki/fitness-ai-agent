from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in Docker
    load_dotenv = None


DEFAULT_DATABASE_PATH = "/data/fitness.db"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_OPENAI_VISION_MODEL = "gpt-4.1"


@dataclass(frozen=True)
class AppConfig:
    telegram_bot_token: str | None = None
    openai_api_key: str | None = None
    database_path: str = DEFAULT_DATABASE_PATH
    allowed_telegram_user_ids: frozenset[int] = field(default_factory=frozenset)
    timezone: str = DEFAULT_TIMEZONE
    openai_vision_model: str = DEFAULT_OPENAI_VISION_MODEL
    reminders_enabled: bool = True
    weigh_in_reminder_time: str = "07:30"
    meal_log_reminder_time: str = "14:00"
    workout_reminder_time: str = "18:00"
    daily_summary_reminder_time: str = "21:00"
    weekly_summary_day: str = "sunday"
    weekly_summary_reminder_time: str = "19:00"

    def log_safe_summary(self) -> str:
        allowlist_mode = "open" if not self.allowed_telegram_user_ids else "restricted"
        return (
            f"database_path={self.database_path}; "
            f"timezone={self.timezone}; "
            f"allowlist_mode={allowlist_mode}; "
            f"reminders_enabled={self.reminders_enabled}"
        )


def parse_allowed_user_ids(raw_value: str | None) -> frozenset[int]:
    if raw_value is None or not raw_value.strip():
        return frozenset()

    parsed_ids: set[int] = set()
    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            parsed_ids.add(int(value))
        except ValueError as exc:
            raise ValueError(
                "ALLOWED_TELEGRAM_USER_IDS must contain comma-separated integers"
            ) from exc
    return frozenset(parsed_ids)


def parse_bool(raw_value: str | None, *, default: bool) -> bool:
    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value: {raw_value}")


def load_config(env: Mapping[str, str] | None = None) -> AppConfig:
    if env is None:
        if load_dotenv is not None:
            load_dotenv()
        env = os.environ

    return AppConfig(
        telegram_bot_token=_optional_env(env.get("TELEGRAM_BOT_TOKEN")),
        openai_api_key=_optional_env(env.get("OPENAI_API_KEY")),
        database_path=_env_or_default(env, "DATABASE_PATH", DEFAULT_DATABASE_PATH),
        allowed_telegram_user_ids=parse_allowed_user_ids(
            env.get("ALLOWED_TELEGRAM_USER_IDS")
        ),
        timezone=_env_or_default(env, "TIMEZONE", DEFAULT_TIMEZONE),
        openai_vision_model=_env_or_default(
            env,
            "OPENAI_VISION_MODEL",
            DEFAULT_OPENAI_VISION_MODEL,
        ),
        reminders_enabled=parse_bool(env.get("REMINDERS_ENABLED"), default=True),
        weigh_in_reminder_time=_env_or_default(
            env, "WEIGH_IN_REMINDER_TIME", "07:30"
        ),
        meal_log_reminder_time=_env_or_default(env, "MEAL_LOG_REMINDER_TIME", "14:00"),
        workout_reminder_time=_env_or_default(env, "WORKOUT_REMINDER_TIME", "18:00"),
        daily_summary_reminder_time=_env_or_default(
            env, "DAILY_SUMMARY_REMINDER_TIME", "21:00"
        ),
        weekly_summary_day=_env_or_default(env, "WEEKLY_SUMMARY_DAY", "sunday"),
        weekly_summary_reminder_time=_env_or_default(
            env, "WEEKLY_SUMMARY_REMINDER_TIME", "19:00"
        ),
    )


def require_telegram_bot_token(config: AppConfig) -> str:
    if not config.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for real bot startup")
    return config.telegram_bot_token


def _optional_env(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _env_or_default(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key)
    if value is None or not value.strip():
        return default
    return value.strip()
