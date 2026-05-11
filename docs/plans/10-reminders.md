# Reminders

## Scope

Reminders are part of the Telegram bot itself rather than an external automation service.

Use APScheduler, preferably `AsyncIOScheduler`, inside the same Python process as Telegram polling. Default timezone comes from configuration.

## Phase 1 Reminder Types

- weigh-in: daily 07:30
- meal logging: daily 14:00
- workout/cardio: daily 18:00
- daily check-in: daily 21:00
- weekly review: Sunday 19:00

Use fixed templates in Phase 1. Do not call OpenAI for normal reminders.

## Commands

- `/reminders`: show enabled status, timezone, schedule, and how to turn off
- `/reminders_on`: enable reminders, ensure chat ID exists, register jobs
- `/reminders_off`: disable reminders and remove jobs, without deleting schedule settings

Future: `/set_reminder`, snooze, quiet hours, workday/weekend schedules, missed-log nudges, automatic summaries.

## Settings

Store both `telegram_user_id` and `chat_id`, because Telegram sends to chat IDs.

`/start` should create user profile, save user/chat IDs, and create default reminder settings if missing. User-specific SQLite settings override env defaults.

If reminders are enabled but no chat ID is known, ask the user to send `/start`.

## Environment Defaults

`.env.example` should include:

```env
TIMEZONE=UTC
REMINDERS_ENABLED=true
WEIGH_IN_REMINDER_TIME=07:30
MEAL_LOG_REMINDER_TIME=14:00
WORKOUT_REMINDER_TIME=18:00
DAILY_SUMMARY_REMINDER_TIME=21:00
WEEKLY_SUMMARY_DAY=sunday
WEEKLY_SUMMARY_REMINDER_TIME=19:00
```

## Scheduler Lifecycle

Startup: load config, initialize DB, initialize Telegram app, initialize scheduler, load enabled reminder settings, register jobs, start scheduler, start polling.

Shutdown: gracefully shut down scheduler if possible and log shutdown.

Stable job IDs:

- `reminder:{telegram_user_id}:weigh_in`
- `reminder:{telegram_user_id}:meal_log`
- `reminder:{telegram_user_id}:workout`
- `reminder:{telegram_user_id}:daily_summary`
- `reminder:{telegram_user_id}:weekly_summary`

Use `replace_existing=True` or remove jobs before registering to avoid duplicates.

Configure scheduler jobs so missed reminders are not backfilled after downtime. Use APScheduler settings such as a small `misfire_grace_time` and appropriate coalescing behavior, and test that startup does not send old missed reminders.

## Downtime Rule

If the container is offline during reminder time, do not send missed reminders on startup. Resume future reminders only.

## Safety

Only allowed and known users receive reminders. If a user is no longer allowed, skip sending and optionally disable reminders for that user.

Reminder messages should avoid sensitive detail such as measurements, progress notes, raw food logs, or photo analysis.

## Testing

Do not wait for real time. Test default settings, env parsing, stable job IDs, enable/disable, duplicate prevention, timezone, fake send-message, startup loading, user isolation, and workout reminder text based on plan/completion state.
