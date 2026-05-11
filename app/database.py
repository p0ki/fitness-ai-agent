from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


SCHEMA_V1_VERSION = 1
SCHEMA_V1_NAME = "sqlite_memory_foundation"
SCHEMA_V2_VERSION = 2
SCHEMA_V2_NAME = "core_fitness_logging"
SCHEMA_V3_VERSION = 3
SCHEMA_V3_NAME = "privacy_admin"
SCHEMA_V4_VERSION = 4
SCHEMA_V4_NAME = "food_photos"
SCHEMA_V5_VERSION = 5
SCHEMA_V5_NAME = "progress_photos"


@contextmanager
def connect(database_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(database_path: str) -> None:
    path = Path(database_path)
    if database_path != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    with connect(database_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL,
                applied_at_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL UNIQUE,
                chat_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                nickname TEXT,
                profile_summary TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT,
                UNIQUE (telegram_user_id, key)
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                memory_text TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS raw_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                telegram_message_id INTEGER,
                chat_id INTEGER,
                message_type TEXT NOT NULL,
                message_text TEXT,
                caption TEXT,
                created_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                ai_extracted_facts_json TEXT NOT NULL DEFAULT '{}',
                linked_record_type TEXT,
                linked_record_id INTEGER,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                calories_estimate REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                fiber_g REAL,
                confidence TEXT NOT NULL DEFAULT 'low',
                source TEXT NOT NULL,
                notes TEXT,
                logged_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                workout_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                duration_minutes INTEGER,
                intensity TEXT,
                source TEXT NOT NULL,
                notes TEXT,
                logged_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS body_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                measurement_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                source TEXT NOT NULL,
                notes TEXT,
                logged_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                local_date TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                summary_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                week_start_date TEXT NOT NULL,
                week_end_date TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                summary_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS pending_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                confirmation_phrase TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                expires_at_utc TEXT NOT NULL,
                completed_at_utc TEXT,
                cancelled_at_utc TEXT,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS photo_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                raw_message_id INTEGER,
                telegram_message_id INTEGER,
                telegram_file_id TEXT NOT NULL,
                telegram_file_unique_id TEXT,
                photo_type TEXT NOT NULL,
                caption TEXT,
                ai_description TEXT,
                analysis_json TEXT NOT NULL DEFAULT '{}',
                confidence TEXT NOT NULL DEFAULT 'low',
                analysis_status TEXT NOT NULL,
                analysis_error TEXT,
                stored_locally INTEGER NOT NULL DEFAULT 0,
                local_path TEXT,
                linked_record_type TEXT,
                linked_record_id INTEGER,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS pending_meal_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                photo_log_id INTEGER NOT NULL,
                raw_message_id INTEGER,
                estimated_description TEXT NOT NULL,
                estimate_json TEXT NOT NULL DEFAULT '{}',
                calories_estimate REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                fiber_g REAL,
                confidence TEXT NOT NULL DEFAULT 'low',
                status TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                expires_at_utc TEXT NOT NULL,
                completed_at_utc TEXT,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS progress_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                photo_log_id INTEGER NOT NULL,
                telegram_message_id INTEGER,
                telegram_file_id TEXT NOT NULL,
                telegram_file_unique_id TEXT,
                taken_at_utc TEXT NOT NULL,
                local_date TEXT NOT NULL,
                angle TEXT NOT NULL,
                user_note TEXT,
                ai_description TEXT NOT NULL,
                comparison_conditions_json TEXT NOT NULL DEFAULT '{}',
                visible_notes_json TEXT NOT NULL DEFAULT '[]',
                strict_feedback TEXT NOT NULL,
                visual_body_fat_estimate_range TEXT,
                visual_body_fat_confidence TEXT NOT NULL DEFAULT 'low',
                estimate_type TEXT NOT NULL DEFAULT 'visual_only',
                overall_confidence TEXT NOT NULL DEFAULT 'low',
                stored_locally INTEGER NOT NULL DEFAULT 0,
                local_path TEXT,
                comparison_photo_id INTEGER,
                is_baseline INTEGER NOT NULL DEFAULT 0,
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                deleted_at TEXT,
                deleted_reason TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_user_profile_user_deleted
                ON user_profile (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_settings_user_key_deleted
                ON settings (telegram_user_id, key, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_memories_user_deleted
                ON memories (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_raw_messages_user_local_date
                ON raw_messages (telegram_user_id, local_date);
            CREATE INDEX IF NOT EXISTS idx_raw_messages_user_created
                ON raw_messages (telegram_user_id, created_at_utc);
            CREATE INDEX IF NOT EXISTS idx_raw_messages_user_deleted
                ON raw_messages (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_meals_user_local_date
                ON meals (telegram_user_id, local_date);
            CREATE INDEX IF NOT EXISTS idx_meals_user_deleted
                ON meals (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_workouts_user_local_date
                ON workouts (telegram_user_id, local_date);
            CREATE INDEX IF NOT EXISTS idx_workouts_user_deleted
                ON workouts (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_body_measurements_user_local_date
                ON body_measurements (telegram_user_id, local_date);
            CREATE INDEX IF NOT EXISTS idx_body_measurements_user_deleted
                ON body_measurements (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_local_date
                ON daily_summaries (telegram_user_id, local_date, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_weekly_summaries_user_date_range
                ON weekly_summaries (
                    telegram_user_id,
                    week_start_date,
                    week_end_date,
                    deleted_at
                );
            CREATE INDEX IF NOT EXISTS idx_pending_actions_user_status
                ON pending_actions (telegram_user_id, status, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_pending_actions_user_expires
                ON pending_actions (telegram_user_id, expires_at_utc);
            CREATE INDEX IF NOT EXISTS idx_photo_logs_user_deleted
                ON photo_logs (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_photo_logs_user_local_date
                ON photo_logs (telegram_user_id, local_date, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_photo_logs_user_status
                ON photo_logs (telegram_user_id, analysis_status, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_photo_logs_raw_message
                ON photo_logs (raw_message_id);
            CREATE INDEX IF NOT EXISTS idx_photo_logs_linked_record
                ON photo_logs (
                    telegram_user_id,
                    linked_record_type,
                    linked_record_id,
                    deleted_at
                );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_photo_logs_user_message
                ON photo_logs (telegram_user_id, telegram_message_id)
                WHERE deleted_at IS NULL AND telegram_message_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_pending_meal_estimates_user_deleted
                ON pending_meal_estimates (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_pending_meal_estimates_user_status
                ON pending_meal_estimates (telegram_user_id, status, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_pending_meal_estimates_raw_message
                ON pending_meal_estimates (raw_message_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_meal_estimates_photo_status
                ON pending_meal_estimates (photo_log_id)
                WHERE status = 'pending' AND deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_progress_photos_user
                ON progress_photos (telegram_user_id);
            CREATE INDEX IF NOT EXISTS idx_progress_photos_user_local_date
                ON progress_photos (telegram_user_id, local_date);
            CREATE INDEX IF NOT EXISTS idx_progress_photos_user_created
                ON progress_photos (telegram_user_id, created_at_utc);
            CREATE INDEX IF NOT EXISTS idx_progress_photos_user_deleted
                ON progress_photos (telegram_user_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_progress_photos_photo_log
                ON progress_photos (photo_log_id);
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, name, applied_at_utc)
            VALUES
                (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (SCHEMA_V1_VERSION, SCHEMA_V1_NAME),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, name, applied_at_utc)
            VALUES
                (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (SCHEMA_V2_VERSION, SCHEMA_V2_NAME),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, name, applied_at_utc)
            VALUES
                (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (SCHEMA_V3_VERSION, SCHEMA_V3_NAME),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, name, applied_at_utc)
            VALUES
                (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (SCHEMA_V4_VERSION, SCHEMA_V4_NAME),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, name, applied_at_utc)
            VALUES
                (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (SCHEMA_V5_VERSION, SCHEMA_V5_NAME),
        )
