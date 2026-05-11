from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.fitness_logging import log_meal
from app.openai_client import (
    FoodPhotoAnalysis,
    FoodPhotoAnalysisError,
    OpenAIFoodPhotoClient,
    OpenAIProgressPhotoClient,
    ProgressPhotoAnalysis,
    ProgressPhotoAnalysisError,
    analyze_food_photo,
    analyze_progress_photo,
)
from app.parsers import ParsedMeal


PENDING_MEAL_STATUS_VALUES = {
    "pending",
    "confirmed",
    "corrected",
    "cancelled",
    "expired",
}
PHOTO_ANALYSIS_STATUS_VALUES = {"pending", "analyzed", "failed", "cancelled"}
PENDING_MEAL_EXPIRY_HOURS = 24
CONFIRMATION_WORDS = {"yes", "save", "log it"}
REJECTION_WORDS = {"no", "cancel"}
FAST_PATH_CAPTIONS = (
    "log this meal",
    "save this meal",
    "track this",
    "this is my lunch",
    "this is my dinner",
)


async def process_food_photo(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    telegram_message_id: int | None,
    chat_id: int | None,
    caption: str | None,
    photo_sizes: list[object],
    config: AppConfig,
    ai_client: object | None = None,
    raw_message_id: int | None = None,
    now_utc: datetime | None = None,
) -> str:
    del chat_id
    selected_photo = _select_largest_photo_size(photo_sizes)
    if selected_photo is None:
        return "I could not find a usable photo. Try sending it again."

    raw_file_id = _photo_attr(selected_photo, "file_id")
    file_id = raw_file_id or "unknown"
    file_unique_id = _photo_attr(selected_photo, "file_unique_id")
    existing = _existing_photo_log(
        conn,
        telegram_user_id,
        telegram_message_id,
        file_unique_id,
        raw_file_id,
    )
    if existing is not None:
        return _duplicate_photo_reply(conn, telegram_user_id, existing)

    now = _normalize_utc(now_utc)
    timestamp = _to_iso(now)
    local_date = _local_date(now, config.timezone)
    photo_log_id = _create_photo_log(
        conn,
        telegram_user_id=telegram_user_id,
        raw_message_id=raw_message_id,
        telegram_message_id=telegram_message_id,
        telegram_file_id=file_id,
        telegram_file_unique_id=file_unique_id,
        photo_type="food",
        caption=caption,
        analysis_status="pending",
        created_at_utc=timestamp,
        local_date=local_date,
    )

    temp_path: Path | None = None
    try:
        temp_path = _temp_photo_path(config.database_path, file_id)
        await _download_photo(selected_photo, temp_path)
        analysis = analyze_food_photo(
            str(temp_path),
            caption=caption,
            client=_food_photo_client(config, ai_client),
        )
    except Exception as exc:
        analysis_error = _analysis_error_text(exc)
        _mark_photo_analysis_failed(conn, photo_log_id, analysis_error, _to_iso(_utc_now()))
        if "non-food" in analysis_error.lower():
            return "I can only handle food photos here. Try /log_meal manually."
        return (
            "I couldn't analyze that food photo properly.\n"
            "Log it manually with:\n"
            "/log_meal 3 eggs and tuna"
        )
    finally:
        _delete_temp_file(temp_path)

    if analysis.photo_type != "food":
        _mark_photo_analysis_failed(
            conn,
            photo_log_id,
            "Unsupported or unclear photo type.",
            _to_iso(_utc_now()),
        )
        return "I can only handle food photos here. Try /log_meal manually."

    _mark_photo_analyzed(conn, photo_log_id, analysis, _to_iso(_utc_now()))
    if _is_fast_path_caption(caption) and analysis.confidence != "low":
        meal_id = _save_meal_from_analysis(
            conn,
            telegram_user_id=telegram_user_id,
            analysis=analysis,
            source="food_photo_fast_log",
            timezone_name=config.timezone,
            now_utc=now,
        )
        _link_photo_to_meal(conn, photo_log_id, meal_id, _to_iso(_utc_now()))
        return (
            "Saved as an estimate.\n"
            f"Confidence: {analysis.confidence}.\n\n"
            "Correct it by using /delete_last and logging it again if wrong."
        )

    _create_pending_meal_estimate(
        conn,
        telegram_user_id=telegram_user_id,
        photo_log_id=photo_log_id,
        raw_message_id=raw_message_id,
        analysis=analysis,
        now_utc=now,
    )
    return _format_food_estimate_reply(analysis)


async def process_progress_photo(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    telegram_message_id: int | None,
    chat_id: int | None,
    caption: str | None,
    photo_sizes: list[object],
    config: AppConfig,
    ai_client: object | None = None,
    raw_message_id: int | None = None,
    now_utc: datetime | None = None,
) -> str:
    del chat_id
    selected_photo = _select_largest_photo_size(photo_sizes)
    if selected_photo is None:
        return "I could not find a usable photo. Try sending it again."

    raw_file_id = _photo_attr(selected_photo, "file_id")
    file_id = raw_file_id or "unknown"
    file_unique_id = _photo_attr(selected_photo, "file_unique_id")
    existing = _existing_photo_log(
        conn,
        telegram_user_id,
        telegram_message_id,
        file_unique_id,
        raw_file_id,
    )
    if existing is not None:
        return _duplicate_progress_photo_reply(conn, telegram_user_id, existing)

    now = _normalize_utc(now_utc)
    timestamp = _to_iso(now)
    local_date = _local_date(now, config.timezone)
    photo_log_id = _create_photo_log(
        conn,
        telegram_user_id=telegram_user_id,
        raw_message_id=raw_message_id,
        telegram_message_id=telegram_message_id,
        telegram_file_id=file_id,
        telegram_file_unique_id=file_unique_id,
        photo_type="progress",
        caption=caption,
        analysis_status="pending",
        created_at_utc=timestamp,
        local_date=local_date,
    )

    temp_path: Path | None = None
    downloaded = False
    try:
        temp_path = _temp_photo_path(config.database_path, file_id, photo_type="progress")
        await _download_photo(selected_photo, temp_path)
        downloaded = True
        previous = _latest_progress_photo(conn, telegram_user_id)
        analysis = analyze_progress_photo(
            str(temp_path),
            caption=caption,
            context=_progress_analysis_context(previous),
            client=_progress_photo_client(config, ai_client),
        )
        progress_photo_id = _create_progress_photo(
            conn,
            telegram_user_id=telegram_user_id,
            photo_log_id=photo_log_id,
            telegram_message_id=telegram_message_id,
            telegram_file_id=file_id,
            telegram_file_unique_id=file_unique_id,
            caption=caption,
            analysis=analysis,
            comparison_photo_id=int(previous["id"]) if previous is not None else None,
            is_baseline=previous is None,
            now_utc=now,
            local_date=local_date,
        )
        _mark_progress_photo_analyzed(
            conn,
            photo_log_id,
            progress_photo_id,
            analysis,
            _to_iso(_utc_now()),
        )
    except Exception as exc:
        analysis_error = _analysis_error_text(exc)
        _mark_photo_analysis_failed(conn, photo_log_id, analysis_error, _to_iso(_utc_now()))
        lowered = analysis_error.lower()
        if not downloaded or "download failed" in lowered:
            return (
                "I couldn't download that progress photo. "
                "Try sending it again or log a note manually."
            )
        if "openai_api_key" in lowered:
            return (
                "I saved the photo metadata, but progress-photo analysis needs OpenAI "
                "configured. Set OPENAI_API_KEY, or add a manual note for now."
            )
        if "non-progress" in lowered:
            return "I can only handle progress photos here. Is this food, progress, or ignore?"
        return (
            "I couldn't analyze that progress photo properly.\n"
            "Progress-photo analysis needs a clear body progress photo and OpenAI vision."
        )
    finally:
        _delete_temp_file(temp_path)

    return _format_progress_photo_reply(
        analysis,
        is_baseline=previous is None,
    )


def has_pending_meal_estimate(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> bool:
    return _latest_pending_estimate(conn, telegram_user_id) is not None


def is_pending_meal_response(text: str) -> bool:
    lowered = text.strip().lower()
    return (
        lowered in CONFIRMATION_WORDS
        or lowered in REJECTION_WORDS
        or lowered.startswith("edit:")
    )


def handle_pending_meal_text(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    text: str,
    *,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> str:
    now = _normalize_utc(now_utc)
    pending = _latest_pending_estimate(conn, telegram_user_id)
    if pending is None:
        return "No pending meal found. Send a food photo or use /log_meal."

    if datetime.fromisoformat(pending["expires_at_utc"]) < now:
        conn.execute(
            """
            UPDATE pending_meal_estimates
            SET status = 'expired',
                updated_at_utc = ?
            WHERE id = ?
            """,
            (_to_iso(now), pending["id"]),
        )
        return "That pending meal estimate expired. No meal was saved."

    lowered = text.strip().lower()
    if lowered in REJECTION_WORDS:
        _set_pending_status(conn, int(pending["id"]), "cancelled", now)
        return "Cancelled. I did not save this as a meal."

    if lowered.startswith("edit:"):
        correction_text = text.split(":", 1)[1].strip()
        if len(correction_text) < 3:
            return "Tell me the correction after edit:, for example: edit: 650 kcal, 50g protein"
        meal_id = _save_corrected_pending_meal(
            conn,
            telegram_user_id,
            pending,
            correction_text,
            timezone_name=timezone_name,
            now_utc=now,
        )
        _set_pending_status(conn, int(pending["id"]), "corrected", now)
        _link_photo_to_meal(conn, int(pending["photo_log_id"]), meal_id, _to_iso(now))
        return "Saved corrected meal."

    if lowered in CONFIRMATION_WORDS:
        analysis = _analysis_from_pending(pending)
        if analysis.confidence == "low":
            return "Confidence is low. Correct it first with: edit: what this meal actually was."
        meal_id = _save_meal_from_analysis(
            conn,
            telegram_user_id=telegram_user_id,
            analysis=analysis,
            source="food_photo_confirmed",
            timezone_name=timezone_name,
            now_utc=now,
        )
        _set_pending_status(conn, int(pending["id"]), "confirmed", now)
        _link_photo_to_meal(conn, int(pending["photo_log_id"]), meal_id, _to_iso(now))
        return "Saved meal from photo estimate."

    return "Reply yes / edit: ... / no."


def cancel_pending_meal_estimates(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    now_utc: datetime | None = None,
) -> int:
    now = _normalize_utc(now_utc)
    cursor = conn.execute(
        """
        UPDATE pending_meal_estimates
        SET status = 'cancelled',
            updated_at_utc = ?
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        """,
        (_to_iso(now), telegram_user_id),
    )
    return int(cursor.rowcount)


def _select_largest_photo_size(photo_sizes: list[object]) -> object | None:
    if not photo_sizes:
        return None
    return max(photo_sizes, key=_photo_size_score)


def _food_photo_client(config: AppConfig, ai_client: object | None) -> object | None:
    if ai_client is not None:
        return ai_client
    if not config.openai_api_key:
        return None
    return OpenAIFoodPhotoClient(config.openai_api_key, config.openai_vision_model)


def _progress_photo_client(config: AppConfig, ai_client: object | None) -> object | None:
    if ai_client is not None:
        return ai_client
    if not config.openai_api_key:
        return None
    return OpenAIProgressPhotoClient(config.openai_api_key, config.openai_vision_model)


def _photo_size_score(photo_size: object) -> int:
    file_size = getattr(photo_size, "file_size", None)
    if isinstance(file_size, int):
        return file_size
    width = getattr(photo_size, "width", 0)
    height = getattr(photo_size, "height", 0)
    if isinstance(width, int) and isinstance(height, int):
        return width * height
    return 0


async def _download_photo(photo_size: object, temp_path: Path) -> None:
    telegram_file = await photo_size.get_file()
    try:
        await telegram_file.download_to_drive(custom_path=temp_path)
    except TypeError:
        await telegram_file.download_to_drive(temp_path)


def _create_photo_log(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    raw_message_id: int | None,
    telegram_message_id: int | None,
    telegram_file_id: str,
    telegram_file_unique_id: str | None,
    photo_type: str,
    caption: str | None,
    analysis_status: str,
    created_at_utc: str,
    local_date: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO photo_logs
            (
                telegram_user_id,
                raw_message_id,
                telegram_message_id,
                telegram_file_id,
                telegram_file_unique_id,
                photo_type,
                caption,
                ai_description,
                analysis_json,
                confidence,
                analysis_status,
                analysis_error,
                stored_locally,
                local_path,
                created_at_utc,
                updated_at_utc,
                local_date
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, '{}', 'low', ?, NULL, 0, NULL, ?, ?, ?)
        """,
        (
            telegram_user_id,
            raw_message_id,
            telegram_message_id,
            telegram_file_id,
            telegram_file_unique_id,
            photo_type,
            caption,
            analysis_status,
            created_at_utc,
            created_at_utc,
            local_date,
        ),
    )
    return int(cursor.lastrowid)


def _create_progress_photo(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    photo_log_id: int,
    telegram_message_id: int | None,
    telegram_file_id: str,
    telegram_file_unique_id: str | None,
    caption: str | None,
    analysis: ProgressPhotoAnalysis,
    comparison_photo_id: int | None,
    is_baseline: bool,
    now_utc: datetime,
    local_date: str,
) -> int:
    timestamp = _to_iso(now_utc)
    cursor = conn.execute(
        """
        INSERT INTO progress_photos
            (
                telegram_user_id,
                photo_log_id,
                telegram_message_id,
                telegram_file_id,
                telegram_file_unique_id,
                taken_at_utc,
                local_date,
                angle,
                user_note,
                ai_description,
                comparison_conditions_json,
                visible_notes_json,
                strict_feedback,
                visual_body_fat_estimate_range,
                visual_body_fat_confidence,
                estimate_type,
                overall_confidence,
                stored_locally,
                local_path,
                comparison_photo_id,
                is_baseline,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            photo_log_id,
            telegram_message_id,
            telegram_file_id,
            telegram_file_unique_id,
            timestamp,
            local_date,
            analysis.angle,
            caption,
            analysis.ai_description,
            json.dumps(analysis.comparison_conditions, sort_keys=True),
            json.dumps(analysis.visible_notes, sort_keys=True),
            analysis.strict_feedback,
            analysis.visual_body_fat_estimate_range,
            analysis.visual_body_fat_confidence,
            analysis.estimate_type,
            analysis.overall_confidence,
            comparison_photo_id,
            1 if is_baseline else 0,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def _create_pending_meal_estimate(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    photo_log_id: int,
    raw_message_id: int | None,
    analysis: FoodPhotoAnalysis,
    now_utc: datetime,
) -> int:
    timestamp = _to_iso(now_utc)
    expires = _to_iso(now_utc + timedelta(hours=PENDING_MEAL_EXPIRY_HOURS))
    cursor = conn.execute(
        """
        INSERT INTO pending_meal_estimates
            (
                telegram_user_id,
                photo_log_id,
                raw_message_id,
                estimated_description,
                estimate_json,
                calories_estimate,
                protein_g,
                carbs_g,
                fat_g,
                fiber_g,
                confidence,
                status,
                created_at_utc,
                updated_at_utc,
                expires_at_utc
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            telegram_user_id,
            photo_log_id,
            raw_message_id,
            _analysis_description(analysis),
            json.dumps(asdict(analysis), sort_keys=True),
            analysis.calories_estimate,
            analysis.protein_g,
            analysis.carbs_g,
            analysis.fat_g,
            analysis.fiber_g,
            analysis.confidence,
            timestamp,
            timestamp,
            expires,
        ),
    )
    return int(cursor.lastrowid)


def _mark_photo_analyzed(
    conn: sqlite3.Connection,
    photo_log_id: int,
    analysis: FoodPhotoAnalysis,
    updated_at_utc: str,
) -> None:
    conn.execute(
        """
        UPDATE photo_logs
        SET ai_description = ?,
            analysis_json = ?,
            confidence = ?,
            analysis_status = 'analyzed',
            analysis_error = NULL,
            updated_at_utc = ?
        WHERE id = ?
        """,
        (
            analysis.ai_description,
            json.dumps(asdict(analysis), sort_keys=True),
            analysis.confidence,
            updated_at_utc,
            photo_log_id,
        ),
    )


def _mark_progress_photo_analyzed(
    conn: sqlite3.Connection,
    photo_log_id: int,
    progress_photo_id: int,
    analysis: ProgressPhotoAnalysis,
    updated_at_utc: str,
) -> None:
    conn.execute(
        """
        UPDATE photo_logs
        SET ai_description = ?,
            analysis_json = ?,
            confidence = ?,
            analysis_status = 'analyzed',
            analysis_error = NULL,
            linked_record_type = 'progress_photos',
            linked_record_id = ?,
            updated_at_utc = ?
        WHERE id = ?
        """,
        (
            analysis.ai_description,
            json.dumps(asdict(analysis), sort_keys=True),
            analysis.overall_confidence,
            progress_photo_id,
            updated_at_utc,
            photo_log_id,
        ),
    )


def _mark_photo_analysis_failed(
    conn: sqlite3.Connection,
    photo_log_id: int,
    analysis_error: str,
    updated_at_utc: str,
) -> None:
    conn.execute(
        """
        UPDATE photo_logs
        SET analysis_status = 'failed',
            analysis_error = ?,
            updated_at_utc = ?
        WHERE id = ?
        """,
        (analysis_error, updated_at_utc, photo_log_id),
    )


def _save_meal_from_analysis(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    analysis: FoodPhotoAnalysis,
    source: str,
    timezone_name: str,
    now_utc: datetime,
) -> int:
    meal = ParsedMeal(
        description=_analysis_description(analysis),
        calories_estimate=analysis.calories_estimate,
        protein_g=analysis.protein_g,
        carbs_g=analysis.carbs_g,
        fat_g=analysis.fat_g,
        fiber_g=analysis.fiber_g,
        confidence=analysis.confidence,
        source=source,
        notes=_notes_from_analysis(analysis),
    )
    return log_meal(
        conn,
        telegram_user_id=telegram_user_id,
        meal=meal,
        timezone_name=timezone_name,
        now_utc=now_utc,
    )


def _save_corrected_pending_meal(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    pending: sqlite3.Row,
    correction_text: str,
    *,
    timezone_name: str,
    now_utc: datetime,
) -> int:
    analysis = _analysis_from_pending(pending)
    calories = _extract_number(correction_text, r"(\d+(?:[\.,]\d+)?)\s*kcal")
    protein = _extract_number(correction_text, r"(\d+(?:[\.,]\d+)?)\s*g?\s*protein")
    meal = ParsedMeal(
        description=correction_text,
        calories_estimate=calories if calories is not None else analysis.calories_estimate,
        protein_g=protein if protein is not None else analysis.protein_g,
        carbs_g=analysis.carbs_g,
        fat_g=analysis.fat_g,
        fiber_g=analysis.fiber_g,
        confidence=analysis.confidence,
        source="correction",
        notes="Corrected from food photo estimate.",
    )
    return log_meal(
        conn,
        telegram_user_id=telegram_user_id,
        meal=meal,
        timezone_name=timezone_name,
        now_utc=now_utc,
    )


def _link_photo_to_meal(
    conn: sqlite3.Connection,
    photo_log_id: int,
    meal_id: int,
    updated_at_utc: str,
) -> None:
    conn.execute(
        """
        UPDATE photo_logs
        SET linked_record_type = 'meals',
            linked_record_id = ?,
            updated_at_utc = ?
        WHERE id = ?
        """,
        (meal_id, updated_at_utc, photo_log_id),
    )


def _latest_pending_estimate(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM pending_meal_estimates
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        ORDER BY created_at_utc DESC, id DESC
        LIMIT 1
        """,
        (telegram_user_id,),
    ).fetchone()


def _existing_photo_log(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    telegram_message_id: int | None,
    telegram_file_unique_id: str | None,
    telegram_file_id: str | None,
) -> sqlite3.Row | None:
    if telegram_message_id is not None:
        existing = conn.execute(
            """
            SELECT *
            FROM photo_logs
            WHERE telegram_user_id = ?
              AND telegram_message_id = ?
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (telegram_user_id, telegram_message_id),
        ).fetchone()
        if existing is not None:
            return existing

    if telegram_file_unique_id is not None:
        return conn.execute(
            """
            SELECT *
            FROM photo_logs
            WHERE telegram_user_id = ?
              AND telegram_file_unique_id = ?
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (telegram_user_id, telegram_file_unique_id),
        ).fetchone()

    if telegram_file_id is not None:
        return conn.execute(
            """
            SELECT *
            FROM photo_logs
            WHERE telegram_user_id = ?
              AND telegram_file_id = ?
              AND telegram_file_unique_id IS NULL
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (telegram_user_id, telegram_file_id),
        ).fetchone()

    return None


def _duplicate_photo_reply(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    photo_log: sqlite3.Row,
) -> str:
    pending = conn.execute(
        """
        SELECT 1
        FROM pending_meal_estimates
        WHERE telegram_user_id = ?
          AND photo_log_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (telegram_user_id, photo_log["id"]),
    ).fetchone()
    if pending is not None:
        return "I already have a pending estimate for that photo. Reply yes / edit: ... / no."
    if photo_log["linked_record_id"] is not None:
        return "That meal was already saved."
    return "That photo was already processed."


def _duplicate_progress_photo_reply(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    photo_log: sqlite3.Row,
) -> str:
    progress = conn.execute(
        """
        SELECT 1
        FROM progress_photos
        WHERE telegram_user_id = ?
          AND photo_log_id = ?
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (telegram_user_id, photo_log["id"]),
    ).fetchone()
    if progress is not None:
        return "That progress photo was already processed."
    if photo_log["linked_record_id"] is not None:
        return "That photo was already processed."
    return "That photo was already processed."


def _set_pending_status(
    conn: sqlite3.Connection,
    pending_id: int,
    status: str,
    now: datetime,
) -> None:
    completed = _to_iso(now) if status in {"confirmed", "corrected"} else None
    conn.execute(
        """
        UPDATE pending_meal_estimates
        SET status = ?,
            updated_at_utc = ?,
            completed_at_utc = COALESCE(?, completed_at_utc)
        WHERE id = ?
        """,
        (status, _to_iso(now), completed, pending_id),
    )


def _analysis_from_pending(pending: sqlite3.Row) -> FoodPhotoAnalysis:
    payload = json.loads(pending["estimate_json"])
    if "photo_type" not in payload:
        description = str(pending["estimated_description"])
        return FoodPhotoAnalysis(
            photo_type="food",
            ai_description=description,
            detected_foods=[description],
            portion_assumptions=[],
            calories_estimate=_optional_float(pending["calories_estimate"]),
            protein_g=_optional_float(pending["protein_g"]),
            carbs_g=_optional_float(pending["carbs_g"]),
            fat_g=_optional_float(pending["fat_g"]),
            fiber_g=_optional_float(pending["fiber_g"]),
            confidence=str(pending["confidence"]),
            uncertainty_notes=[],
            needs_confirmation=True,
            suggested_user_question=None,
        )
    return FoodPhotoAnalysis(
        photo_type=str(payload["photo_type"]),
        ai_description=str(payload["ai_description"]),
        detected_foods=[str(item) for item in payload["detected_foods"]],
        portion_assumptions=[str(item) for item in payload["portion_assumptions"]],
        calories_estimate=_optional_float(payload.get("calories_estimate")),
        protein_g=_optional_float(payload.get("protein_g")),
        carbs_g=_optional_float(payload.get("carbs_g")),
        fat_g=_optional_float(payload.get("fat_g")),
        fiber_g=_optional_float(payload.get("fiber_g")),
        confidence=str(payload["confidence"]),
        uncertainty_notes=[str(item) for item in payload["uncertainty_notes"]],
        needs_confirmation=bool(payload["needs_confirmation"]),
        suggested_user_question=payload.get("suggested_user_question"),
    )


def _format_food_estimate_reply(analysis: FoodPhotoAnalysis) -> str:
    foods = ", ".join(analysis.detected_foods)
    assumptions = "\n".join(f"- {item}" for item in analysis.portion_assumptions)
    uncertainty = "\n".join(f"- {item}" for item in analysis.uncertainty_notes)
    intro = "Food estimate:"
    if analysis.confidence == "low":
        intro = "Food estimate (low confidence - correct this before saving):"
    return (
        f"{intro}\n"
        f"- likely: {foods}\n"
        f"- calories: ~{_format_number(analysis.calories_estimate)} kcal\n"
        f"- protein: ~{_format_number(analysis.protein_g)}g\n"
        f"- carbs: ~{_format_number(analysis.carbs_g)}g\n"
        f"- fat: ~{_format_number(analysis.fat_g)}g\n"
        f"- fiber: ~{_format_number(analysis.fiber_g)}g\n"
        f"Confidence: {analysis.confidence}\n\n"
        "Assumptions:\n"
        f"{assumptions or '- portion size is estimated'}\n\n"
        "Uncertainty:\n"
        f"{uncertainty or '- none noted'}\n\n"
        "Save this meal?\n"
        "Reply:\n"
        "yes / edit: ... / no"
    )


def _format_progress_photo_reply(
    analysis: ProgressPhotoAnalysis,
    *,
    is_baseline: bool,
) -> str:
    notes = "\n".join(f"- {item}" for item in analysis.visible_notes)
    guidance = "\n".join(f"- {item}" for item in analysis.standardized_photo_guidance)
    body_fat = analysis.visual_body_fat_estimate_range or "no useful visual estimate"
    intro = "Baseline saved." if is_baseline else "Comparison saved."
    comparison_note = (
        "Future comparisons need the same lighting, distance, angle, and pose."
        if is_baseline
        else "Comparison is cautious because photos can lie when lighting, pose, distance, or clothing changes."
    )
    return (
        f"{intro}\n"
        f"{comparison_note}\n\n"
        "Progress notes:\n"
        f"{notes or '- no clear visible notes'}\n\n"
        f"Visual-only body-fat: {body_fat}\n"
        f"Confidence: {analysis.visual_body_fat_confidence}\n\n"
        "No-BS feedback:\n"
        f"{analysis.strict_feedback}\n\n"
        "Next photo:\n"
        f"{guidance or '- same lighting, distance, front/side/back angles'}"
    )


def _analysis_description(analysis: FoodPhotoAnalysis) -> str:
    if analysis.detected_foods:
        return ", ".join(analysis.detected_foods)
    return analysis.ai_description


def _notes_from_analysis(analysis: FoodPhotoAnalysis) -> str | None:
    notes = [*analysis.portion_assumptions, *analysis.uncertainty_notes]
    if not notes:
        return None
    return " | ".join(notes)


def _is_fast_path_caption(caption: str | None) -> bool:
    if caption is None:
        return False
    lowered = caption.strip().lower()
    return any(phrase in lowered for phrase in FAST_PATH_CAPTIONS)


def _latest_progress_photo(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM progress_photos
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        ORDER BY created_at_utc DESC, id DESC
        LIMIT 1
        """,
        (telegram_user_id,),
    ).fetchone()


def _progress_analysis_context(previous: sqlite3.Row | None) -> dict[str, object]:
    if previous is None:
        return {"has_previous_progress_photo": False}
    return {
        "has_previous_progress_photo": True,
        "previous_angle": previous["angle"],
        "previous_local_date": previous["local_date"],
        "previous_overall_confidence": previous["overall_confidence"],
    }


def _temp_photo_path(database_path: str, file_id: str, *, photo_type: str = "food") -> Path:
    if database_path == ":memory:":
        temp_dir = Path(".test-data") / "temp"
    else:
        temp_dir = Path(database_path).parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    safe_file_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", file_id)[:40] or "photo"
    safe_photo_type = re.sub(r"[^A-Za-z0-9_.-]+", "_", photo_type)[:20] or "photo"
    return temp_dir / f"{safe_photo_type}_{safe_file_id}_{uuid4().hex}.jpg"


def _delete_temp_file(temp_path: Path | None) -> None:
    if temp_path is None:
        return
    try:
        temp_path.unlink(missing_ok=True)
    except OSError:
        pass


def _photo_attr(photo_size: object, attr_name: str) -> str | None:
    value = getattr(photo_size, attr_name, None)
    if isinstance(value, str) and value:
        return value
    return None


def _analysis_error_text(exc: Exception) -> str:
    if isinstance(exc, FoodPhotoAnalysisError | ProgressPhotoAnalysisError):
        return str(exc)
    return f"{exc.__class__.__name__}: {exc}"


def _extract_number(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, re.I)
    if match is None:
        return None
    return float(match.group(1).replace(",", "."))


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return "?"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _normalize_utc(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _local_date(exact_utc: datetime, timezone_name: str) -> str:
    return exact_utc.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _to_iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")
