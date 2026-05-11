# 0006: Telegram Polling Reminders

Date: 2026-05-04

Status: approved

## Context

The bot should send simple fitness reminders for weigh-ins, meal logging, workout/cardio, daily check-ins, and weekly reviews. It will run on Unraid without public ports.

## Decision

Use APScheduler inside the bot process. Reminders are user-facing Telegram bot functionality, not an external automation service.

Store reminder settings in SQLite with `telegram_user_id` and `chat_id`. Use the configured timezone by default. Do not backfill missed reminders after downtime.

Configure APScheduler jobs to avoid stale reminder delivery after container downtime, using settings such as a small `misfire_grace_time` and appropriate coalescing behavior. Startup must not send old missed reminders.

## Consequences

Reminders work on Unraid with polling and no public URL. Container restarts reload settings from SQLite and register future jobs.

Reminder messages should be fixed templates in Phase 1 and should not call OpenAI by default.

Related docs: `docs/plans/10-reminders.md`.
