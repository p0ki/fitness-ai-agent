from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.parsers import ParsedMeal, ParsedMeasurement, ParsedWorkout


def log_meal(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    meal: ParsedMeal,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> int:
    exact_utc = _normalize_utc(now_utc)
    timestamp = exact_utc.isoformat(timespec="seconds")
    local_date = _local_date(exact_utc, timezone_name)
    cursor = conn.execute(
        """
        INSERT INTO meals
            (
                telegram_user_id,
                description,
                calories_estimate,
                protein_g,
                carbs_g,
                fat_g,
                fiber_g,
                confidence,
                source,
                notes,
                logged_at_utc,
                local_date,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            meal.description,
            meal.calories_estimate,
            meal.protein_g,
            meal.carbs_g,
            meal.fat_g,
            meal.fiber_g,
            meal.confidence,
            meal.source,
            meal.notes,
            timestamp,
            local_date,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def list_meals(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    local_date: str | None = None,
) -> list[sqlite3.Row]:
    params: list[object] = [telegram_user_id]
    date_filter = ""
    if local_date is not None:
        date_filter = "AND local_date = ?"
        params.append(local_date)
    return conn.execute(
        f"""
        SELECT *
        FROM meals
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
          {date_filter}
        ORDER BY logged_at_utc, id
        """,
        params,
    ).fetchall()


def log_body_measurement(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    measurement: ParsedMeasurement,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> int:
    exact_utc = _normalize_utc(now_utc)
    timestamp = exact_utc.isoformat(timespec="seconds")
    local_date = _local_date(exact_utc, timezone_name)
    cursor = conn.execute(
        """
        INSERT INTO body_measurements
            (
                telegram_user_id,
                measurement_type,
                value,
                unit,
                source,
                notes,
                logged_at_utc,
                local_date,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            measurement.measurement_type,
            measurement.value,
            measurement.unit,
            measurement.source,
            measurement.notes,
            timestamp,
            local_date,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def list_body_measurements(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    local_date: str | None = None,
) -> list[sqlite3.Row]:
    params: list[object] = [telegram_user_id]
    date_filter = ""
    if local_date is not None:
        date_filter = "AND local_date = ?"
        params.append(local_date)
    return conn.execute(
        f"""
        SELECT *
        FROM body_measurements
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
          {date_filter}
        ORDER BY logged_at_utc, id
        """,
        params,
    ).fetchall()


def log_workout(
    conn: sqlite3.Connection,
    *,
    telegram_user_id: int,
    workout: ParsedWorkout,
    timezone_name: str,
    now_utc: datetime | None = None,
) -> int:
    exact_utc = _normalize_utc(now_utc)
    timestamp = exact_utc.isoformat(timespec="seconds")
    local_date = _local_date(exact_utc, timezone_name)
    cursor = conn.execute(
        """
        INSERT INTO workouts
            (
                telegram_user_id,
                workout_type,
                summary,
                duration_minutes,
                intensity,
                source,
                notes,
                logged_at_utc,
                local_date,
                created_at_utc,
                updated_at_utc
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            workout.workout_type,
            workout.summary,
            workout.duration_minutes,
            workout.intensity,
            workout.source,
            workout.notes,
            timestamp,
            local_date,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def list_workouts(
    conn: sqlite3.Connection,
    telegram_user_id: int,
    *,
    local_date: str | None = None,
) -> list[sqlite3.Row]:
    params: list[object] = [telegram_user_id]
    date_filter = ""
    if local_date is not None:
        date_filter = "AND local_date = ?"
        params.append(local_date)
    return conn.execute(
        f"""
        SELECT *
        FROM workouts
        WHERE telegram_user_id = ?
          AND deleted_at IS NULL
          {date_filter}
        ORDER BY logged_at_utc, id
        """,
        params,
    ).fetchall()


def _normalize_utc(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _local_date(exact_utc: datetime, timezone_name: str) -> str:
    return exact_utc.astimezone(ZoneInfo(timezone_name)).date().isoformat()
