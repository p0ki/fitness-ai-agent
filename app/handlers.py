from __future__ import annotations

from collections.abc import Awaitable, Callable
import sqlite3

from app.admin import (
    build_privacy_reply,
    cancel_pending_actions,
    confirm_pending_action,
    create_backup,
    create_export,
    has_pending_action,
    prepare_delete_all_data,
    prepare_delete_last,
    prepare_delete_range,
    prepare_delete_today,
)
from app.config import AppConfig
from app.database import connect
from app.fitness_logging import log_body_measurement, log_meal, log_workout
from app.memory import (
    build_data_summary_reply,
    build_memory_reply,
    build_profile_reply,
    log_raw_message,
    seed_user_profile,
)
from app.openai_client import StructuredLogValidationError, extract_structured_log
from app.parsers import (
    ParsedMeal,
    ParsedMeasurement,
    ParsedWorkout,
    parse_meal,
    parse_measurement,
    parse_weight,
    parse_workout,
)
from app.photos import (
    cancel_pending_meal_estimates,
    handle_pending_meal_text,
    has_pending_meal_estimate,
    is_pending_meal_response,
    process_food_photo,
    process_progress_photo,
)
from app.summaries import generate_daily_summary, generate_weekly_summary
from app.utils import is_authorized_user


def route_text_command(
    text: str,
    telegram_user_id: int | None,
    config: AppConfig,
    *,
    conn: sqlite3.Connection | None = None,
    chat_id: int | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    ai_client: object | None = None,
) -> str | None:
    if not is_authorized_user(telegram_user_id, config):
        return None

    command = text.strip().split(maxsplit=1)[0].lower()
    if command == "/start":
        if conn is not None:
            seed_user_profile(
                conn,
                telegram_user_id,
                chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                timezone_name=config.timezone,
            )
        return build_start_reply()
    if command == "/help":
        return build_help_reply()
    if command == "/privacy":
        return build_privacy_reply(config)
    if command == "/profile":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return build_profile_reply(conn, telegram_user_id)
    if command == "/memory":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return build_memory_reply(conn, telegram_user_id)
    if command == "/data_summary":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return build_data_summary_reply(conn, telegram_user_id)
    if command == "/export":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return create_export(conn, telegram_user_id, config).reply
    if command == "/backup":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return create_backup(conn, config).reply
    if command == "/delete_last":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return prepare_delete_last(conn, telegram_user_id, config).reply
    if command == "/delete_today":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return prepare_delete_today(conn, telegram_user_id, config).reply
    if command == "/delete_range":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return prepare_delete_range(
            conn,
            telegram_user_id,
            config,
            _command_args(text),
        ).reply
    if command == "/delete_all_data":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return prepare_delete_all_data(conn, telegram_user_id, config).reply
    if command == "/cancel":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        cancelled_admin = cancel_pending_actions(conn, telegram_user_id)
        cancelled_meals = cancel_pending_meal_estimates(conn, telegram_user_id)
        if cancelled_admin or cancelled_meals:
            if cancelled_meals:
                return "Cancelled. I did not save this as a meal."
            return "Cancelled. No changes were applied."
        return "No pending action to cancel."
    if command == "/log_weight":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        try:
            measurement = parse_weight(text)
        except ValueError as exc:
            return f"I could not log that weight. {exc}"
        log_body_measurement(
            conn,
            telegram_user_id=telegram_user_id,
            measurement=measurement,
            timezone_name=config.timezone,
        )
        return f"Logged weight: {_format_number(measurement.value)} {measurement.unit}."
    if command == "/log_measurement":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        try:
            measurement = parse_measurement(text)
        except ValueError as exc:
            return f"I could not log that measurement. {exc}"
        log_body_measurement(
            conn,
            telegram_user_id=telegram_user_id,
            measurement=measurement,
            timezone_name=config.timezone,
        )
        return (
            f"Logged {measurement.measurement_type}: "
            f"{_format_number(measurement.value)} {measurement.unit}."
        )
    if command == "/log_meal":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        try:
            meal = parse_meal(text)
        except ValueError as exc:
            return f"I could not log that meal. {exc}"
        log_meal(
            conn,
            telegram_user_id=telegram_user_id,
            meal=meal,
            timezone_name=config.timezone,
        )
        return (
            f"Logged meal: {meal.description}.\n"
            "No-BS: estimates stay rough until calories/macros are added later."
        )
    if command == "/log_workout":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        try:
            workout = parse_workout(text)
        except ValueError as exc:
            return f"I could not log that workout. {exc}"
        log_workout(
            conn,
            telegram_user_id=telegram_user_id,
            workout=workout,
            timezone_name=config.timezone,
        )
        return f"Logged workout: {workout.summary}."
    if command == "/summary_today":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return generate_daily_summary(conn, telegram_user_id, timezone_name=config.timezone)
    if command == "/summary_week":
        if conn is None:
            return "Database is not ready yet. Try /start again."
        return generate_weekly_summary(conn, telegram_user_id, timezone_name=config.timezone)

    if not command.startswith("/"):
        if conn is not None and has_pending_action(conn, telegram_user_id):
            return confirm_pending_action(conn, telegram_user_id, text).reply
        if conn is not None and (
            has_pending_meal_estimate(conn, telegram_user_id)
            or is_pending_meal_response(text)
        ):
            return handle_pending_meal_text(
                conn,
                telegram_user_id,
                text,
                timezone_name=config.timezone,
            )
        return _route_natural_text(
            text,
            telegram_user_id,
            config,
            conn=conn,
            ai_client=ai_client,
        )

    return "I do not know that command yet. Use /help for the current basics."


def build_start_reply() -> str:
    return (
        "Fitness AI agent is awake.\n\n"
        "Food and progress photo logging are available.\n\n"
        "Use /help for examples."
    )


def build_help_reply() -> str:
    return (
        "Quick examples:\n"
        "- weighed 80.0\n"
        "- ate 3 eggs and tuna\n"
        "- did 30 min bike\n"
        "- plan tomorrow\n"
        "- send a food photo\n\n"
        "Available now:\n"
        "- /start\n"
        "- /help\n\n"
        "- /profile\n"
        "- /memory\n"
        "- /summary_today\n"
        "- /summary_week\n"
        "- /data_summary\n"
        "- /privacy\n"
        "- /export\n"
        "- /backup\n"
        "- /delete_last\n"
        "- /delete_today\n"
        "- /delete_range 2026-05-01 2026-05-07\n"
        "- /delete_all_data\n"
        "- /cancel\n"
        "- /log_weight 80.0\n"
        "- /log_meal 3 eggs and tuna\n"
        "- /log_workout 30 min bike\n"
        "- /log_measurement waist 88 cm\n\n"
        "Planned later:\n"
        "- /equipment\n"
        "- /add_plate 2x10kg\n\n"
        "No-BS: log the basics first. Fancy comes later."
    )


def register_handlers(application: object, config: AppConfig) -> None:
    from telegram.ext import CommandHandler, MessageHandler, filters

    application.add_handler(CommandHandler("start", make_command_callback("/start", config)))
    application.add_handler(CommandHandler("help", make_command_callback("/help", config)))
    application.add_handler(
        CommandHandler("profile", make_command_callback("/profile", config))
    )
    application.add_handler(
        CommandHandler("memory", make_command_callback("/memory", config))
    )
    application.add_handler(
        CommandHandler("data_summary", make_command_callback("/data_summary", config))
    )
    application.add_handler(
        CommandHandler("privacy", make_command_callback("/privacy", config))
    )
    application.add_handler(
        CommandHandler("export", make_command_callback("/export", config))
    )
    application.add_handler(
        CommandHandler("backup", make_command_callback("/backup", config))
    )
    application.add_handler(
        CommandHandler("delete_last", make_command_callback("/delete_last", config))
    )
    application.add_handler(
        CommandHandler("delete_today", make_command_callback("/delete_today", config))
    )
    application.add_handler(
        CommandHandler("delete_range", make_command_callback("/delete_range", config))
    )
    application.add_handler(
        CommandHandler(
            "delete_all_data",
            make_command_callback("/delete_all_data", config),
        )
    )
    application.add_handler(
        CommandHandler("cancel", make_command_callback("/cancel", config))
    )
    application.add_handler(
        CommandHandler("log_weight", make_command_callback("/log_weight", config))
    )
    application.add_handler(
        CommandHandler(
            "log_measurement",
            make_command_callback("/log_measurement", config),
        )
    )
    application.add_handler(
        CommandHandler("log_meal", make_command_callback("/log_meal", config))
    )
    application.add_handler(
        CommandHandler("log_workout", make_command_callback("/log_workout", config))
    )
    application.add_handler(
        CommandHandler(
            "summary_today",
            make_command_callback("/summary_today", config),
        )
    )
    application.add_handler(
        CommandHandler("summary_week", make_command_callback("/summary_week", config))
    )
    application.add_handler(MessageHandler(filters.PHOTO, make_photo_callback(config)))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, make_text_callback(config))
    )


def make_command_callback(
    command_text: str,
    config: AppConfig,
) -> Callable[[object, object], Awaitable[None]]:
    async def callback(update: object, context: object) -> None:
        del context
        message = getattr(update, "message", None)
        actual_text = getattr(message, "text", None) if message is not None else None
        await reply_to_update(update, actual_text or command_text, config)

    return callback


def make_text_callback(
    config: AppConfig,
) -> Callable[[object, object], Awaitable[None]]:
    async def callback(update: object, context: object) -> None:
        del context
        message = getattr(update, "message", None)
        text = getattr(message, "text", None) if message is not None else None
        await reply_to_update(update, text or "", config)

    return callback


def make_photo_callback(
    config: AppConfig,
) -> Callable[[object, object], Awaitable[None]]:
    async def callback(update: object, context: object) -> None:
        del context
        await reply_to_photo_update(update, config)

    return callback


async def reply_to_update(update: object, text: str, config: AppConfig) -> None:
    telegram_user_id = _extract_user_id(update)
    if not is_authorized_user(telegram_user_id, config):
        return

    message = getattr(update, "message", None)
    if message is None:
        return

    actual_text = getattr(message, "text", None) or text
    with connect(config.database_path) as conn:
        log_raw_message(
            conn,
            telegram_user_id=telegram_user_id,
            telegram_message_id=_extract_message_id(message),
            chat_id=_extract_chat_id(message),
            message_type="text",
            message_text=actual_text,
            caption=getattr(message, "caption", None),
            timezone_name=config.timezone,
        )
        response = route_text_command(
            actual_text,
            telegram_user_id,
            config,
            conn=conn,
            chat_id=_extract_chat_id(message),
            username=_extract_user_attr(update, "username"),
            first_name=_extract_user_attr(update, "first_name"),
            last_name=_extract_user_attr(update, "last_name"),
        )

    if response is None:
        return

    await message.reply_text(response)


async def reply_to_photo_update(
    update: object,
    config: AppConfig,
    *,
    ai_client: object | None = None,
) -> None:
    telegram_user_id = _extract_user_id(update)
    if not is_authorized_user(telegram_user_id, config):
        return

    message = getattr(update, "message", None)
    if message is None:
        return

    caption = getattr(message, "caption", None)
    photo_route = _route_photo_caption(caption)
    if photo_route == "unclear":
        with connect(config.database_path) as conn:
            log_raw_message(
                conn,
                telegram_user_id=telegram_user_id,
                telegram_message_id=_extract_message_id(message),
                chat_id=_extract_chat_id(message),
                message_type="photo",
                message_text=None,
                caption=caption,
                timezone_name=config.timezone,
            )
        await message.reply_text("Is this food, progress, or ignore?")
        return

    with connect(config.database_path) as conn:
        raw_message_id = log_raw_message(
            conn,
            telegram_user_id=telegram_user_id,
            telegram_message_id=_extract_message_id(message),
            chat_id=_extract_chat_id(message),
            message_type="photo",
            message_text=None,
            caption=caption,
            timezone_name=config.timezone,
        )
        process_photo = (
            process_progress_photo if photo_route == "progress" else process_food_photo
        )
        response = await process_photo(
            conn,
            telegram_user_id=telegram_user_id,
            telegram_message_id=_extract_message_id(message),
            chat_id=_extract_chat_id(message),
            caption=caption,
            photo_sizes=list(getattr(message, "photo", []) or []),
            config=config,
            ai_client=ai_client,
            raw_message_id=raw_message_id,
        )

    if response is None:
        return

    await message.reply_text(response)


def _extract_user_id(update: object) -> int | None:
    user = getattr(update, "effective_user", None)
    user_id = getattr(user, "id", None)
    if isinstance(user_id, int):
        return user_id
    return None


def _extract_user_attr(update: object, attr_name: str) -> str | None:
    user = getattr(update, "effective_user", None)
    value = getattr(user, attr_name, None)
    if isinstance(value, str) and value:
        return value
    return None


def _extract_message_id(message: object) -> int | None:
    message_id = getattr(message, "message_id", None)
    if isinstance(message_id, int):
        return message_id
    return None


def _extract_chat_id(message: object) -> int | None:
    chat = getattr(message, "chat", None)
    chat_id = getattr(chat, "id", None)
    if isinstance(chat_id, int):
        return chat_id
    return None


def _route_photo_caption(caption: str | None) -> str:
    if caption is None or not caption.strip():
        return "unclear"

    lowered = f" {caption.strip().lower()} "
    food_markers = (
        " food",
        " meal",
        " breakfast",
        " lunch",
        " dinner",
        " snack",
        " ate ",
        " eating ",
        " calorie",
        " kcal",
        " protein",
        " plate",
        " log this meal",
        " save this meal",
        " track this",
    )
    progress_markers = (
        " progress",
        " body",
        " physique",
        " check-in",
        " checkin",
        " front",
        " side",
        " back",
        " waist",
    )
    if any(marker in lowered for marker in food_markers):
        return "food"
    if any(marker in lowered for marker in progress_markers):
        return "progress"
    return "unclear"


def _route_natural_text(
    text: str,
    telegram_user_id: int,
    config: AppConfig,
    *,
    conn: sqlite3.Connection | None,
    ai_client: object | None,
) -> str:
    if conn is None:
        return "Database is not ready yet. Try /start again."

    lowered = text.strip().lower()
    if lowered.startswith(("weighed ", "weight ")):
        try:
            measurement = parse_weight(text)
        except ValueError:
            return _clarify_log_reply()
        log_body_measurement(
            conn,
            telegram_user_id=telegram_user_id,
            measurement=measurement,
            timezone_name=config.timezone,
        )
        return f"Logged weight: {_format_number(measurement.value)} {measurement.unit}."
    if lowered.startswith(("waist ", "bellybutton waist ", "hips ", "hip ")):
        try:
            measurement = parse_measurement(text)
        except ValueError:
            return _clarify_log_reply()
        log_body_measurement(
            conn,
            telegram_user_id=telegram_user_id,
            measurement=measurement,
            timezone_name=config.timezone,
        )
        return (
            f"Logged {measurement.measurement_type}: "
            f"{_format_number(measurement.value)} {measurement.unit}."
        )
    if lowered.startswith(("did ", "completed ", "finished ")) or " min " in lowered:
        try:
            workout = parse_workout(text)
        except ValueError:
            return _clarify_log_reply()
        log_workout(
            conn,
            telegram_user_id=telegram_user_id,
            workout=workout,
            timezone_name=config.timezone,
        )
        return f"Logged workout: {workout.summary}."
    if lowered.startswith(("ate ", "had ")):
        try:
            meal = parse_meal(text)
        except ValueError:
            return _clarify_log_reply()
        log_meal(
            conn,
            telegram_user_id=telegram_user_id,
            meal=meal,
            timezone_name=config.timezone,
        )
        return (
            f"Logged meal: {meal.description}.\n"
            "No-BS: unlogged snacks still count."
        )

    return _route_ai_extracted_text(
        text,
        telegram_user_id,
        config,
        conn=conn,
        ai_client=ai_client,
    )


def _route_ai_extracted_text(
    text: str,
    telegram_user_id: int,
    config: AppConfig,
    *,
    conn: sqlite3.Connection,
    ai_client: object | None,
) -> str:
    try:
        extraction = extract_structured_log(
            text,
            context={"timezone": config.timezone},
            client=ai_client,
        )
    except StructuredLogValidationError:
        return _clarify_log_reply()

    if extraction.needs_clarification:
        return extraction.clarification_question or _clarify_log_reply()

    data = extraction.data
    try:
        if extraction.intent == "meal":
            description = _required_text(data.get("description"))
            meal = ParsedMeal(
                description=description,
                calories_estimate=_optional_float(data.get("calories_estimate")),
                protein_g=_optional_float(data.get("protein_g")),
                carbs_g=_optional_float(data.get("carbs_g")),
                fat_g=_optional_float(data.get("fat_g")),
                fiber_g=_optional_float(data.get("fiber_g")),
                confidence=extraction.confidence,
                source="ai_extracted",
            )
            log_meal(
                conn,
                telegram_user_id=telegram_user_id,
                meal=meal,
                timezone_name=config.timezone,
            )
            return f"Logged meal: {meal.description}."
        if extraction.intent in {"weight", "measurement"}:
            measurement = ParsedMeasurement(
                measurement_type=_required_text(
                    data.get("measurement_type") or extraction.intent
                ),
                value=_required_float(data.get("value")),
                unit=_required_text(data.get("unit") or "kg"),
                source="ai_extracted",
            )
            log_body_measurement(
                conn,
                telegram_user_id=telegram_user_id,
                measurement=measurement,
                timezone_name=config.timezone,
            )
            return (
                f"Logged {measurement.measurement_type}: "
                f"{_format_number(measurement.value)} {measurement.unit}."
            )
        if extraction.intent == "workout":
            workout = ParsedWorkout(
                workout_type=_required_text(data.get("workout_type") or "workout"),
                summary=_required_text(data.get("summary")),
                duration_minutes=_optional_int(data.get("duration_minutes")),
                intensity=_optional_text(data.get("intensity")),
                source="ai_extracted",
            )
            log_workout(
                conn,
                telegram_user_id=telegram_user_id,
                workout=workout,
                timezone_name=config.timezone,
            )
            return f"Logged workout: {workout.summary}."
    except ValueError:
        return _clarify_log_reply()

    return _clarify_log_reply()


def _clarify_log_reply() -> str:
    return (
        "I am not sure what to log yet. Try:\n"
        "- /log_meal 3 eggs and tuna\n"
        "- /log_weight 80.0\n"
        "- /log_workout 30 min bike"
    )


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _command_args(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 1:
        return ""
    return parts[1].strip()


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Required text is missing.")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text(value)


def _required_float(value: object) -> float:
    if not isinstance(value, int | float):
        raise ValueError("Required number is missing.")
    return float(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return _required_float(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError("Expected integer.")
    return value
