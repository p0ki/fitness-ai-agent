from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from app.config import AppConfig


YES_DELETE = "YES DELETE"
CONFIRM_DELETE_TODAY = "CONFIRM DELETE TODAY"
CONFIRM_DELETE_RANGE = "CONFIRM DELETE RANGE"
CONFIRM_DELETE_ALL = "CONFIRM DELETE ALL"

PENDING_ACTION_MINUTES = 15


@dataclass(frozen=True)
class AdminReply:
    reply: str


@dataclass(frozen=True)
class FileResult:
    path: Path
    reply: str


USER_TABLES = (
    "user_profile",
    "settings",
    "memories",
    "raw_messages",
    "meals",
    "photo_logs",
    "progress_photos",
    "pending_meal_estimates",
    "workouts",
    "body_measurements",
    "daily_summaries",
    "weekly_summaries",
    "pending_actions",
)

EXPORT_TABLES = (
    "user_profile",
    "settings",
    "memories",
    "meals",
    "photo_logs",
    "progress_photos",
    "pending_meal_estimates",
    "workouts",
    "body_measurements",
    "daily_summaries",
    "weekly_summaries",
)

DELETE_LAST_SPECS = (
    ("meals", "Meal", "description", "logged_at_utc"),
    ("workouts", "Workout", "summary", "logged_at_utc"),
    ("body_measurements", "Measurement", "measurement_type", "logged_at_utc"),
    ("progress_photos", "Progress photo", "ai_description", "created_at_utc"),
    ("daily_summaries", "Daily summary", "summary_text", "created_at_utc"),
    ("weekly_summaries", "Weekly summary", "summary_text", "created_at_utc"),
    ("memories", "Memory", "memory_text", "created_at_utc"),
)

LOCAL_DATE_TABLES = (
    "meals",
    "photo_logs",
    "progress_photos",
    "workouts",
    "body_measurements",
    "daily_summaries",
)


def build_privacy_reply(config: AppConfig) -> str:
    return (
        "Privacy summary:\n\n"
        f"- Database: {config.database_path} inside Docker\n"
        "- Secrets: .env\n"
        "- Photos: not permanently stored in Phase 1\n"
        "- Temporary photos: may be downloaded for analysis, then deleted\n"
        "- Stored photo data: Telegram file ID, metadata, AI notes, estimates, confidence\n"
        "- OpenAI: used for text and image analysis when configured\n"
        "- Raw messages: stored for audit/debugging, not normal memory\n"
        "- Export: /export\n"
        "- Backup: /backup\n"
        "- Delete: /delete_last, /delete_today, /delete_range, /delete_all_data\n\n"
        "No-BS: your data is only useful if you control it. Use /backup before big deletes."
    )


def create_pending_action(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    action_type: str,
    payload: dict[str, object],
    confirmation_phrase: str,
    now_utc: datetime | None = None,
) -> int:
    now = _normalize_utc(now_utc)
    expires = now + timedelta(minutes=PENDING_ACTION_MINUTES)
    conn.execute(
        """
        UPDATE pending_actions
        SET status = 'cancelled',
            cancelled_at_utc = ?
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        """,
        (_to_iso(now), telegram_user_id),
    )
    cursor = conn.execute(
        """
        INSERT INTO pending_actions
            (
                telegram_user_id,
                action_type,
                payload_json,
                confirmation_phrase,
                status,
                created_at_utc,
                expires_at_utc
            )
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            telegram_user_id,
            action_type,
            json.dumps(payload, sort_keys=True),
            confirmation_phrase,
            _to_iso(now),
            _to_iso(expires),
        ),
    )
    return int(cursor.lastrowid)


def get_active_pending_action(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    now_utc: datetime | None = None,
) -> sqlite3.Row | None:
    now = _normalize_utc(now_utc)
    return conn.execute(
        """
        SELECT *
        FROM pending_actions
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
          AND expires_at_utc >= ?
        ORDER BY created_at_utc DESC, id DESC
        LIMIT 1
        """,
        (telegram_user_id, _to_iso(now)),
    ).fetchone()


def has_pending_action(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM pending_actions
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (telegram_user_id,),
    ).fetchone()
    return row is not None


def cancel_pending_actions(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    now_utc: datetime | None = None,
) -> int:
    now = _normalize_utc(now_utc)
    cursor = conn.execute(
        """
        UPDATE pending_actions
        SET status = 'cancelled',
            cancelled_at_utc = ?
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
        """,
        (_to_iso(now), telegram_user_id),
    )
    return int(cursor.rowcount)


def build_cancel_reply(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    now_utc: datetime | None = None,
) -> str:
    cancelled = cancel_pending_actions(conn, telegram_user_id, now_utc=now_utc)
    if cancelled:
        return "Cancelled. No changes were applied."
    return "No pending action to cancel."


def create_export(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    config: AppConfig,
    *,
    now_utc: datetime | None = None,
) -> FileResult:
    now = _normalize_utc(now_utc)
    export_dir = _data_dir(config.database_path) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"fitness_export_{telegram_user_id}_{_file_stamp(now)}.json"
    payload: dict[str, object] = {
        "export_version": 1,
        "exported_at_utc": _to_iso(now),
        "telegram_user_id": telegram_user_id,
    }
    for table_name in EXPORT_TABLES:
        payload[_export_key(table_name)] = _active_rows(conn, table_name, telegram_user_id)

    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return FileResult(
        path=path,
        reply=(
            "Export created.\n"
            f"Path: {path}\n\n"
            "Raw messages and actual image files are excluded by default."
        ),
    )


def create_backup(
    conn: sqlite3.Connection,
    config: AppConfig,
    *,
    now_utc: datetime | None = None,
) -> FileResult:
    now = _normalize_utc(now_utc)
    backup_dir = _data_dir(config.database_path) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"fitness_backup_{_file_stamp(now)}.db"
    destination = sqlite3.connect(path)
    try:
        if config.database_path == ":memory:":
            conn.backup(destination)
        else:
            conn.commit()
            source = sqlite3.connect(config.database_path)
            try:
                source.backup(destination)
            finally:
                source.close()
    finally:
        destination.close()
    return FileResult(
        path=path,
        reply=(
            "Backup created.\n"
            f"Path: {path}\n\n"
            "No-BS: backups are full database copies. Keep them private."
        ),
    )


def prepare_delete_last(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    config: AppConfig,
    *,
    now_utc: datetime | None = None,
) -> AdminReply:
    del config
    candidate = _latest_semantic_record(conn, telegram_user_id)
    if candidate is None:
        return AdminReply("No eligible record found to delete.")

    create_pending_action(
        conn,
        telegram_user_id=telegram_user_id,
        action_type="delete_last",
        payload=candidate,
        confirmation_phrase=YES_DELETE,
        now_utc=now_utc,
    )
    return AdminReply(
        "Last record:\n"
        f"{candidate['label']} - {candidate['description']}\n"
        f"Logged: {candidate['timestamp']}\n\n"
        "Reply exactly:\n"
        f"{YES_DELETE}"
    )


def prepare_delete_today(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    config: AppConfig,
    *,
    now_utc: datetime | None = None,
) -> AdminReply:
    local_day = _local_date(_normalize_utc(now_utc), config.timezone)
    counts = _counts_for_local_range(conn, telegram_user_id, local_day, local_day)
    create_pending_action(
        conn,
        telegram_user_id=telegram_user_id,
        action_type="delete_today",
        payload={"local_date": local_day, "counts": counts},
        confirmation_phrase=CONFIRM_DELETE_TODAY,
        now_utc=now_utc,
    )
    return AdminReply(
        f"This will delete records for {local_day}:\n"
        f"{_format_counts(counts)}\n\n"
        "Reply exactly:\n"
        f"{CONFIRM_DELETE_TODAY}"
    )


def prepare_delete_range(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    config: AppConfig,
    args: str,
    *,
    now_utc: datetime | None = None,
) -> AdminReply:
    del config
    parts = args.split()
    if len(parts) != 2:
        return AdminReply("Use:\n/delete_range YYYY-MM-DD YYYY-MM-DD")
    try:
        start = date.fromisoformat(parts[0])
        end = date.fromisoformat(parts[1])
    except ValueError:
        return AdminReply("Use:\n/delete_range YYYY-MM-DD YYYY-MM-DD")
    if start > end:
        return AdminReply("Start date must be before or equal to end date.")

    counts = _counts_for_local_range(
        conn,
        telegram_user_id,
        start.isoformat(),
        end.isoformat(),
    )
    create_pending_action(
        conn,
        telegram_user_id=telegram_user_id,
        action_type="delete_range",
        payload={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "counts": counts,
        },
        confirmation_phrase=CONFIRM_DELETE_RANGE,
        now_utc=now_utc,
    )
    return AdminReply(
        f"This will delete records from {start.isoformat()} to {end.isoformat()}:\n"
        f"{_format_counts(counts)}\n\n"
        "Reply exactly:\n"
        f"{CONFIRM_DELETE_RANGE}"
    )


def prepare_delete_all_data(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    config: AppConfig,
    *,
    now_utc: datetime | None = None,
) -> AdminReply:
    del config
    counts = {
        table_name: _active_count(conn, table_name, telegram_user_id)
        for table_name in USER_TABLES
    }
    create_pending_action(
        conn,
        telegram_user_id=telegram_user_id,
        action_type="delete_all_data",
        payload={"counts": counts},
        confirmation_phrase=CONFIRM_DELETE_ALL,
        now_utc=now_utc,
    )
    return AdminReply(
        "Danger zone.\n\n"
        "This will soft-delete all stored bot data for your Telegram user ID.\n"
        f"{_format_counts(counts)}\n\n"
        "Run /backup first if needed.\n\n"
        "Reply exactly:\n"
        f"{CONFIRM_DELETE_ALL}"
    )


def confirm_pending_action(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    confirmation_text: str,
    *,
    now_utc: datetime | None = None,
) -> AdminReply:
    now = _normalize_utc(now_utc)
    active = get_active_pending_action(conn, telegram_user_id, now_utc=now)
    if active is None:
        expired = _latest_expired_pending_action(conn, telegram_user_id, now)
        if expired is not None:
            _mark_action_expired(conn, int(expired["id"]), now)
            return AdminReply("That confirmation expired. No changes were applied.")
        return AdminReply("No pending confirmation found.")

    if confirmation_text.strip() != active["confirmation_phrase"]:
        return AdminReply("Confirmation did not match. No changes were applied.")

    try:
        with conn:
            payload = json.loads(active["payload_json"])
            summary = _execute_pending_action(
                conn,
                telegram_user_id,
                active["action_type"],
                payload,
                now,
            )
            conn.execute(
                """
                UPDATE pending_actions
                SET status = 'completed',
                    completed_at_utc = ?
                WHERE id = ?
                """,
                (_to_iso(now), active["id"]),
            )
    except Exception:
        return AdminReply("Delete failed. No changes were applied.")

    return AdminReply(summary)


def _execute_pending_action(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    action_type: str,
    payload: dict[str, object],
    now: datetime,
) -> str:
    if action_type == "delete_last":
        table_name = _required_payload_text(payload, "table_name")
        record_id = int(payload["record_id"])
        changed = _soft_delete_by_id(
            conn,
            table_name,
            record_id,
            telegram_user_id,
            "delete_last",
            now,
        )
        return f"Deleted {changed} record."

    if action_type == "delete_today":
        local_day = _required_payload_text(payload, "local_date")
        changed = _soft_delete_local_range(
            conn,
            telegram_user_id,
            local_day,
            local_day,
            "delete_today",
            now,
        )
        return f"Soft-deleted {changed} records for {local_day}."

    if action_type == "delete_range":
        start_date = _required_payload_text(payload, "start_date")
        end_date = _required_payload_text(payload, "end_date")
        changed = _soft_delete_local_range(
            conn,
            telegram_user_id,
            start_date,
            end_date,
            "delete_range",
            now,
        )
        return f"Soft-deleted {changed} records from {start_date} to {end_date}."

    if action_type == "delete_all_data":
        changed = _soft_delete_all_user_data(conn, telegram_user_id, now)
        return f"Soft-deleted {changed} records for your Telegram user ID."

    raise ValueError(f"Unsupported pending action: {action_type}")


def _latest_semantic_record(
    conn: sqlite3.Connection,
    telegram_user_id: int,
) -> dict[str, object] | None:
    candidates: list[dict[str, object]] = []
    for table_name, label, description_column, timestamp_column in DELETE_LAST_SPECS:
        row = conn.execute(
            f"""
            SELECT id, {description_column} AS description, {timestamp_column} AS timestamp
            FROM {table_name}
            WHERE telegram_user_id = ?
              AND deleted_at IS NULL
            ORDER BY {timestamp_column} DESC, id DESC
            LIMIT 1
            """,
            (telegram_user_id,),
        ).fetchone()
        if row is not None:
            description = str(row["description"]).splitlines()[0][:120]
            candidates.append(
                {
                    "table_name": table_name,
                    "record_id": int(row["id"]),
                    "label": label,
                    "description": description,
                    "timestamp": row["timestamp"],
                }
            )
    if not candidates:
        return None
    return max(candidates, key=lambda item: (str(item["timestamp"]), int(item["record_id"])))


def _soft_delete_by_id(
    conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    _validate_user_table(table_name)
    linked_photo_ids: list[int] = []
    if table_name == "meals":
        linked_photo_ids = _linked_photo_ids_for_record(
            conn,
            telegram_user_id,
            "meals",
            record_id,
        )
    if table_name == "progress_photos":
        progress_photo = conn.execute(
            """
            SELECT photo_log_id
            FROM progress_photos
            WHERE id = ?
              AND telegram_user_id = ?
              AND deleted_at IS NULL
            """,
            (record_id, telegram_user_id),
        ).fetchone()
        if progress_photo is not None:
            linked_photo_ids = [int(progress_photo["photo_log_id"])]
    cursor = conn.execute(
        f"""
        UPDATE {table_name}
        SET deleted_at = ?,
            deleted_reason = ?
        WHERE id = ?
          AND telegram_user_id = ?
          AND deleted_at IS NULL
        """,
        (_to_iso(now), reason, record_id, telegram_user_id),
    )
    changed = int(cursor.rowcount)
    changed += _soft_delete_photo_ids(
        conn,
        linked_photo_ids,
        telegram_user_id,
        reason,
        now,
    )
    changed += _soft_delete_pending_for_photo_ids(
        conn,
        linked_photo_ids,
        telegram_user_id,
        reason,
        now,
    )
    if table_name != "progress_photos":
        changed += _soft_delete_progress_for_photo_ids(
            conn,
            linked_photo_ids,
            telegram_user_id,
            reason,
            now,
        )
    return changed


def _soft_delete_local_range(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
    reason: str,
    now: datetime,
) -> int:
    meal_ids = _active_ids_for_local_range(
        conn,
        "meals",
        telegram_user_id,
        start_date,
        end_date,
    )
    photo_ids = _active_ids_for_local_range(
        conn,
        "photo_logs",
        telegram_user_id,
        start_date,
        end_date,
    )
    changed = 0
    for table_name in LOCAL_DATE_TABLES:
        changed += _soft_delete_local_table(
            conn,
            table_name,
            telegram_user_id,
            start_date,
            end_date,
            reason,
            now,
        )
    for meal_id in meal_ids:
        linked_photo_ids = _linked_photo_ids_for_record(
            conn,
            telegram_user_id,
            "meals",
            meal_id,
        )
        changed += _soft_delete_photo_ids(
            conn,
            linked_photo_ids,
            telegram_user_id,
            reason,
            now,
        )
        photo_ids.extend(linked_photo_ids)
    changed += _soft_delete_pending_for_photo_ids(
        conn,
        photo_ids,
        telegram_user_id,
        reason,
        now,
    )
    changed += _soft_delete_progress_for_photo_ids(
        conn,
        photo_ids,
        telegram_user_id,
        reason,
        now,
    )
    return changed


def _soft_delete_local_table(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
    reason: str,
    now: datetime,
) -> int:
    _validate_user_table(table_name)
    cursor = conn.execute(
        f"""
        UPDATE {table_name}
        SET deleted_at = ?,
            deleted_reason = ?
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (_to_iso(now), reason, telegram_user_id, start_date, end_date),
    )
    return int(cursor.rowcount)


def _soft_delete_all_user_data(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    now: datetime,
) -> int:
    changed = 0
    for table_name in USER_TABLES:
        changed += _soft_delete_table_for_user(
            conn,
            table_name,
            telegram_user_id,
            "delete_all_data",
            now,
        )
    return changed


def _soft_delete_table_for_user(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    _validate_user_table(table_name)
    cursor = conn.execute(
        f"""
        UPDATE {table_name}
        SET deleted_at = ?,
            deleted_reason = ?
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        """,
        (_to_iso(now), reason, telegram_user_id),
    )
    return int(cursor.rowcount)


def _counts_for_local_range(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
) -> dict[str, int]:
    return {
        table_name: _active_count_for_local_range(
            conn,
            table_name,
            telegram_user_id,
            start_date,
            end_date,
        )
        for table_name in LOCAL_DATE_TABLES
    }


def _active_count_for_local_range(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
) -> int:
    _validate_user_table(table_name)
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {table_name}
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, start_date, end_date),
    ).fetchone()
    return int(row["count"])


def _active_count(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
) -> int:
    _validate_user_table(table_name)
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


def _active_rows(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
) -> list[dict[str, object]]:
    _validate_user_table(table_name)
    rows = conn.execute(
        f"""
        SELECT *
        FROM {table_name}
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
        ORDER BY id
        """,
        (telegram_user_id,),
    ).fetchall()
    result: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        if table_name in {"photo_logs", "progress_photos"}:
            item["local_path"] = None
        result.append(item)
    return result


def _active_ids_for_local_range(
    conn: sqlite3.Connection,
    table_name: str,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
) -> list[int]:
    _validate_user_table(table_name)
    rows = conn.execute(
        f"""
        SELECT id
        FROM {table_name}
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, start_date, end_date),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _linked_photo_ids_for_record(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    linked_record_type: str,
    linked_record_id: int,
) -> list[int]:
    rows = conn.execute(
        """
        SELECT id
        FROM photo_logs
        WHERE telegram_user_id = ?
          AND linked_record_type = ?
          AND linked_record_id = ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, linked_record_type, linked_record_id),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _soft_delete_photo_ids(
    conn: sqlite3.Connection,
    photo_ids: list[int],
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    changed = 0
    for photo_id in set(photo_ids):
        changed += _soft_delete_by_id_only(
            conn,
            "photo_logs",
            photo_id,
            telegram_user_id,
            reason,
            now,
        )
    return changed


def _soft_delete_pending_for_photo_ids(
    conn: sqlite3.Connection,
    photo_ids: list[int],
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    changed = 0
    for photo_id in set(photo_ids):
        cursor = conn.execute(
            """
            UPDATE pending_meal_estimates
            SET deleted_at = ?,
                deleted_reason = ?
            WHERE telegram_user_id = ?
              AND photo_log_id = ?
              AND deleted_at IS NULL
            """,
            (_to_iso(now), reason, telegram_user_id, photo_id),
        )
        changed += int(cursor.rowcount)
    return changed


def _soft_delete_progress_for_photo_ids(
    conn: sqlite3.Connection,
    photo_ids: list[int],
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    changed = 0
    for photo_id in set(photo_ids):
        cursor = conn.execute(
            """
            UPDATE progress_photos
            SET deleted_at = ?,
                deleted_reason = ?
            WHERE telegram_user_id = ?
              AND photo_log_id = ?
              AND deleted_at IS NULL
            """,
            (_to_iso(now), reason, telegram_user_id, photo_id),
        )
        changed += int(cursor.rowcount)
    return changed


def _soft_delete_by_id_only(
    conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    telegram_user_id: int,
    reason: str,
    now: datetime,
) -> int:
    _validate_user_table(table_name)
    cursor = conn.execute(
        f"""
        UPDATE {table_name}
        SET deleted_at = ?,
            deleted_reason = ?
        WHERE id = ?
          AND telegram_user_id = ?
          AND deleted_at IS NULL
        """,
        (_to_iso(now), reason, record_id, telegram_user_id),
    )
    return int(cursor.rowcount)


def _latest_expired_pending_action(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    now: datetime,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM pending_actions
        WHERE telegram_user_id = ?
          AND status = 'pending'
          AND deleted_at IS NULL
          AND expires_at_utc < ?
        ORDER BY expires_at_utc DESC, id DESC
        LIMIT 1
        """,
        (telegram_user_id, _to_iso(now)),
    ).fetchone()


def _mark_action_expired(
    conn: sqlite3.Connection,
    action_id: int,
    now: datetime,
) -> None:
    conn.execute(
        """
        UPDATE pending_actions
        SET status = 'expired',
            cancelled_at_utc = ?
        WHERE id = ?
        """,
        (_to_iso(now), action_id),
    )


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "- no implemented records"
    lines = []
    for table_name, count in counts.items():
        label = table_name.replace("_", " ")
        lines.append(f"- {label}: {count}")
    return "\n".join(lines)


def _required_payload_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing payload value: {key}")
    return value


def _validate_user_table(table_name: str) -> None:
    if table_name not in USER_TABLES:
        raise ValueError(f"Unsupported user table: {table_name}")


def _export_key(table_name: str) -> str:
    if table_name == "user_profile":
        return "profile"
    return table_name


def _data_dir(database_path: str) -> Path:
    if database_path == ":memory:":
        return Path(".test-data")
    return Path(database_path).parent


def _normalize_utc(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _local_date(exact_utc: datetime, timezone_name: str) -> str:
    from zoneinfo import ZoneInfo

    return exact_utc.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _to_iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _file_stamp(value: datetime) -> str:
    return value.strftime("%Y%m%d_%H%M%S")
