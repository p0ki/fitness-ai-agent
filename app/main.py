from __future__ import annotations

import logging

from app.config import AppConfig, load_config, require_telegram_bot_token
from app.database import init_database
from app.handlers import register_handlers


LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_application(config: AppConfig) -> object:
    token = require_telegram_bot_token(config)

    from telegram.ext import Application

    application = Application.builder().token(token).build()
    register_handlers(application, config)
    return application


def run_bot(config: AppConfig) -> object:
    require_telegram_bot_token(config)
    init_database(config.database_path)
    LOGGER.info("Database initialized at %s", config.database_path)
    application = build_application(config)
    LOGGER.info("Telegram polling starting")
    application.run_polling()
    return application


def main() -> None:
    configure_logging()
    config = load_config()
    LOGGER.info("Config loaded: %s", config.log_safe_summary())
    run_bot(config)


if __name__ == "__main__":
    main()
