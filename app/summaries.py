from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import sqlite3
from zoneinfo import ZoneInfo


def generate_daily_summary(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> str:
    local_day = _local_date(_normalize_utc(now_utc), timezone_name)
    stats = _daily_stats(conn, telegram_user_id, local_day)
    text = _daily_summary_text(local_day, stats)
    _insert_daily_summary(conn, telegram_user_id, local_day, text, stats)
    return text


def generate_weekly_summary(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> str:
    end = date.fromisoformat(_local_date(_normalize_utc(now_utc), timezone_name))
    start = end - timedelta(days=6)
    stats = _range_stats(conn, telegram_user_id, start.isoformat(), end.isoformat())
    text = _weekly_summary_text(start.isoformat(), end.isoformat(), stats)
    _insert_weekly_summary(
        conn,
        telegram_user_id,
        start.isoformat(),
        end.isoformat(),
        text,
        stats,
    )
    return text


def _daily_stats(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    local_day: str,
) -> dict[str, object]:
    stats = _range_stats(conn, telegram_user_id, local_day, local_day)
    latest_weight = conn.execute(
        """
        SELECT value, unit
        FROM body_measurements
        WHERE telegram_user_id = ?
          AND measurement_type = 'weight'
          AND local_date = ?
          AND deleted_at IS NULL
        ORDER BY logged_at_utc DESC, id DESC
        LIMIT 1
        """,
        (telegram_user_id, local_day),
    ).fetchone()
    stats["latest_weight"] = (
        {"value": float(latest_weight["value"]), "unit": latest_weight["unit"]}
        if latest_weight is not None
        else None
    )
    return stats


def _range_stats(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
) -> dict[str, object]:
    meal_row = conn.execute(
        """
        SELECT
            COUNT(*) AS meal_count,
            COALESCE(SUM(calories_estimate), 0) AS calories,
            COALESCE(SUM(protein_g), 0) AS protein
        FROM meals
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, start_date, end_date),
    ).fetchone()
    workout_row = conn.execute(
        """
        SELECT
            COUNT(*) AS workout_count,
            COALESCE(SUM(duration_minutes), 0) AS workout_minutes
        FROM workouts
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, start_date, end_date),
    ).fetchone()
    measurement_row = conn.execute(
        """
        SELECT COUNT(*) AS measurement_count
        FROM body_measurements
        WHERE telegram_user_id = ?
          AND local_date BETWEEN ? AND ?
          AND deleted_at IS NULL
        """,
        (telegram_user_id, start_date, end_date),
    ).fetchone()
    return {
        "meal_count": int(meal_row["meal_count"]),
        "calories": float(meal_row["calories"]),
        "protein": float(meal_row["protein"]),
        "workout_count": int(workout_row["workout_count"]),
        "workout_minutes": int(workout_row["workout_minutes"]),
        "measurement_count": int(measurement_row["measurement_count"]),
    }


def _daily_summary_text(local_day: str, stats: dict[str, object]) -> str:
    if _is_empty_day(stats):
        return (
            f"Today so far: {local_day}\n"
            "No logs for today yet.\n\n"
            "No-BS: right now we have no data, only guesses.\n\n"
            "Next action:\n"
            "Use /log_meal, /log_weight, or /log_workout."
        )

    lines = [
        f"Today so far: {local_day}",
        f"- meals: {stats['meal_count']}",
        f"- calories: ~{_format_number(stats['calories'])} kcal",
        f"- protein: ~{_format_number(stats['protein'])}g",
        f"- workouts: {stats['workout_count']}",
        f"- workout minutes: {_format_number(stats['workout_minutes'])}",
    ]
    latest_weight = stats.get("latest_weight")
    if isinstance(latest_weight, dict):
        lines.append(
            f"- weight: {_format_number(latest_weight['value'])} {latest_weight['unit']}"
        )
    lines.extend(
        [
            "",
            "No-BS: structured data beats guessing.",
            "Next action: log the next meal before memory turns it into fiction.",
        ]
    )
    return "\n".join(lines)


def _weekly_summary_text(
    start_date: str,
    end_date: str,
    stats: dict[str, object],
) -> str:
    lines = [
        f"Week summary: {start_date} to {end_date}",
        f"- meals: {stats['meal_count']}",
        f"- calories: ~{_format_number(stats['calories'])} kcal",
        f"- protein: ~{_format_number(stats['protein'])}g",
        f"- workouts: {stats['workout_count']}",
        f"- workout minutes: {_format_number(stats['workout_minutes'])}",
        f"- measurements: {stats['measurement_count']}",
        "",
        "No-BS: the trend only exists if you log the basics.",
        "Next action: use /summary_today, then log whatever is missing.",
    ]
    return "\n".join(lines)


def _insert_daily_summary(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    local_day: str,
    text: str,
    stats: dict[str, object],
) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO daily_summaries
            (
                telegram_user_id,
                local_date,
                summary_text,
                summary_json,
                source,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, 'deterministic', ?, ?)
        """,
        (telegram_user_id, local_day, text, json.dumps(stats, sort_keys=True), now, now),
    )
    return int(cursor.lastrowid)


def _insert_weekly_summary(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    start_date: str,
    end_date: str,
    text: str,
    stats: dict[str, object],
) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO weekly_summaries
            (
                telegram_user_id,
                week_start_date,
                week_end_date,
                summary_text,
                summary_json,
                source,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, ?, 'deterministic', ?, ?)
        """,
        (
            telegram_user_id,
            start_date,
            end_date,
            text,
            json.dumps(stats, sort_keys=True),
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def _is_empty_day(stats: dict[str, object]) -> bool:
    return (
        stats["meal_count"] == 0
        and stats["workout_count"] == 0
        and stats["measurement_count"] == 0
    )


def _normalize_utc(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _local_date(exact_utc: datetime, timezone_name: str) -> str:
    return exact_utc.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _format_number(value: object) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}".rstrip("0").rstrip(".")
