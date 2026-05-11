from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


INITIAL_PROFILE_SUMMARY = (
    "This is a generic single authorized user fitness profile for a private "
    "Telegram bot. Replace this placeholder through normal profile, memory, "
    "and logging flows with user-approved context. The bot tracks meals, "
    "workouts, body measurements, food-photo estimates, and progress-photo "
    "metadata with strict privacy defaults."
)

DEFAULT_SETTINGS = {
    "strict_mode": "true",
    "timezone": "UTC",
    "preferred_units": "metric",
    "photo_storage_enabled": "false",
}


def seed_user_profile(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    chat_id: int | None,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    timezone_name: str = "UTC",
) -> None:
    now = _utc_now_iso()
    existing = get_profile(conn, telegram_user_id)
    if existing is None:
        conn.execute(
            """
            INSERT INTO user_profile
                (
                    telegram_user_id,
                    chat_id,
                    username,
                    first_name,
                    last_name,
                    nickname,
                    profile_summary,
                    created_at_utc,
                    updated_at_utc
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                chat_id,
                username,
                first_name,
                last_name,
                "personal user",
                INITIAL_PROFILE_SUMMARY,
                now,
                now,
            ),
        )
    else:
        conn.execute(
            """
            UPDATE user_profile
            SET chat_id = ?,
                username = COALESCE(?, username),
                first_name = COALESCE(?, first_name),
                last_name = COALESCE(?, last_name),
                updated_at_utc = ?
            WHERE telegram_user_id = ?
              AND deleted_at IS NULL
            """,
            (chat_id, username, first_name, last_name, now, telegram_user_id),
        )

    settings = dict(DEFAULT_SETTINGS)
    settings["timezone"] = timezone_name
    for key, value in settings.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO settings
                (telegram_user_id, key, value, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_user_id, key, value, now, now),
        )


def get_profile(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM user_profile
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id,),
    ).fetchone()


def get_user_settings(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT key, value
        FROM settings
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        ORDER BY key
        """,
        (telegram_user_id,),
    ).fetchall()
    return {row["key"]: row["value"] for row in rows}


def list_memories(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM memories
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        ORDER BY created_at_utc DESC, id DESC
        """,
        (telegram_user_id,),
    ).fetchall()


def log_raw_message(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    telegram_message_id: int | None,
    chat_id: int | None,
    message_type: str,
    message_text: str | None,
    caption: str | None,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> int:
    exact_utc = _normalize_utc(now_utc)
    created_at_utc = exact_utc.isoformat(timespec="seconds")
    local_date = _local_date(exact_utc, timezone_name)

    cursor = conn.execute(
        """
        INSERT INTO raw_messages
            (
                telegram_user_id,
                telegram_message_id,
                chat_id,
                message_type,
                message_text,
                caption,
                created_at_utc,
                local_date,
                ai_extracted_facts_json,
                linked_record_type,
                linked_record_id
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', NULL, NULL)
        """,
        (
            telegram_user_id,
            telegram_message_id,
            chat_id,
            message_type,
            message_text,
            caption,
            created_at_utc,
            local_date,
        ),
    )
    return int(cursor.lastrowid)


def get_data_summary(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> dict[str, int]:
    return {
        "user_profile": _active_count(conn, "user_profile", telegram_user_id),
        "settings": _active_count(conn, "settings", telegram_user_id),
        "memories": _active_count(conn, "memories", telegram_user_id),
        "raw_messages": _active_count(conn, "raw_messages", telegram_user_id),
        "meals": _active_count(conn, "meals", telegram_user_id),
        "photo_logs": _active_count(conn, "photo_logs", telegram_user_id),
        "progress_photos": _active_count(conn, "progress_photos", telegram_user_id),
        "pending_meal_estimates": _active_count(
            conn,
            "pending_meal_estimates",
            telegram_user_id,
        ),
        "workouts": _active_count(conn, "workouts", telegram_user_id),
        "body_measurements": _active_count(
            conn,
            "body_measurements",
            telegram_user_id,
        ),
        "daily_summaries": _active_count(conn, "daily_summaries", telegram_user_id),
        "weekly_summaries": _active_count(conn, "weekly_summaries", telegram_user_id),
        "pending_actions": _pending_action_count(conn, telegram_user_id),
    }


def build_profile_reply(conn: sqlite3.Connection, telegram_user_id: int) -> str:
    profile = get_profile(conn, telegram_user_id)
    if profile is None:
        return "No profile found yet. Use /start first."

    settings = get_user_settings(conn, telegram_user_id)
    return (
        "Profile:\n"
        f"{profile['profile_summary']}\n\n"
        "Settings:\n"
        f"- strict mode: {settings.get('strict_mode', 'unknown')}\n"
        f"- timezone: {settings.get('timezone', 'unknown')}\n"
        f"- units: {settings.get('preferred_units', 'unknown')}"
    )


def build_memory_reply(conn: sqlite3.Connection, telegram_user_id: int) -> str:
    memories = list_memories(conn, telegram_user_id)
    if not memories:
        return (
            "No curated memories saved yet.\n\n"
            "Raw messages are audit history only; they are not the normal brain."
        )

    lines = ["Curated memories:"]
    lines.extend(f"- {row['memory_text']}" for row in memories[:10])
    return "\n".join(lines)


def build_data_summary_reply(conn: sqlite3.Connection, telegram_user_id: int) -> str:
    summary = get_data_summary(conn, telegram_user_id)
    return (
        "Stored data:\n"
        f"- user profile: {summary['user_profile']}\n"
        f"- settings: {summary['settings']}\n"
        f"- memories: {summary['memories']}\n"
        f"- raw messages: {summary['raw_messages']}\n\n"
        f"- meals: {summary['meals']}\n"
        f"- photo logs: {summary['photo_logs']}\n"
        f"- progress photos: {summary['progress_photos']}\n"
        f"- pending meal estimates: {summary['pending_meal_estimates']}\n"
        f"- workouts: {summary['workouts']}\n"
        f"- body measurements: {summary['body_measurements']}\n"
        f"- daily summaries: {summary['daily_summaries']}\n"
        f"- weekly summaries: {summary['weekly_summaries']}\n"
        f"- pending actions: {summary['pending_actions']}\n\n"
        "Soft-deleted rows are excluded.\n"
        "Planned later: equipment and plans."
    )


def _active_count(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {table_name}
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id,),
    ).fetchone()
    return int(row["count"])


def _pending_action_count(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> int:
    rows = conn.execute(
        """
        SELECT expires_at_utc
        FROM pending_actions
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        """,
        (telegram_user_id,),
    ).fetchall()
    now = datetime.now(timezone.utc)
    count = 0
    for row in rows:
        try:
            expires_at = datetime.fromisoformat(row["expires_at_utc"])
        except ValueError:
            continue
        if expires_at >= now:
            count += 1
    return count


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_utc(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _local_date(exact_utc: datetime, timezone_name: str) -> str:
    return exact_utc.astimezone(ZoneInfo(timezone_name)).date().isoformat()
