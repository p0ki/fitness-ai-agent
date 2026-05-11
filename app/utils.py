from __future__ import annotations

from app.config import AppConfig


def is_authorized_user(telegram_user_id: int | None, config: AppConfig) -> bool:
    if telegram_user_id is None:
        return False
    if not config.allowed_telegram_user_ids:
        return True
    return telegram_user_id in config.allowed_telegram_user_ids
