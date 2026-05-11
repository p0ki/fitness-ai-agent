# Data And Memory

## Memory Layers

The bot uses three memory layers.

Structured fitness data is the source of truth. It powers summaries, trends, planning, progress review, delete/export, and reliable answers.

The compact profile summary stores stable context in `user_profile.profile_summary`. Public defaults must stay generic and must not include real personal health details, measurements, preferences, equipment, or schedule data. Real deployments can replace the generic placeholder through user-approved profile, memory, and logging flows.

Raw audit history stores original messages and photo metadata. It exists for audit, debugging, and future reprocessing. Normal answers should not load raw messages unless the user specifically asks.

## SQLite Rules

Use SQLite at `DATABASE_PATH`, default `/data/fitness.db`.

Every user-owned table includes `telegram_user_id`. Most user-owned tables also include:

- `created_at_utc`
- `updated_at_utc`
- `deleted_at`
- `deleted_reason`

Use UTC ISO timestamps for exact time. Store `local_date` where fitness-day logic matters, using the configured timezone.

Use JSON text columns for flexible data such as AI estimates, extracted facts, plan JSON, alternatives, and source links.

Add simple schema versioning through `schema_migrations` or `app_metadata`.

## Table Groups

Identity and settings:

- `user_profile`
- `settings`
- `reminder_settings`

Memory and audit:

- `memories`
- `raw_messages`
- `photo_logs`

Nutrition:

- `meals`
- `pending_meal_estimates`

Body and progress:

- `body_measurements`
- `progress_photos`

Training and planning:

- `workouts`
- `workout_plans`

Equipment and exercises:

- `equipment`
- `weight_plates`
- `loadable_equipment`
- `exercise_library`
- `exercise_preferences`

Summaries:

- `daily_summaries`
- `weekly_summaries`

Future:

- `research_cache`

## Source And Confidence

Structured records should include source fields such as `manual_command`, `natural_text`, `food_photo_confirmed`, `food_photo_fast_log`, `generated_plan_done`, `ai_extracted`, `seed`, or `correction`.

AI-estimated data must store confidence: low, medium, or high. Confirmed/corrected values become final structured records. Raw AI estimates remain in pending/photo/audit rows where useful.

## Query And Delete Rules

Unauthorized users are blocked before persistence. Normal queries filter by `telegram_user_id` and exclude soft-deleted rows.

Use soft delete where practical. Dangerous operations use transactions and exact confirmation phrases. Export and summaries exclude soft-deleted rows.

## Indexes

Use simple indexes for:

- `telegram_user_id`
- `telegram_user_id, local_date`
- `telegram_user_id, created_at_utc`
- `telegram_user_id, deleted_at`
- `telegram_user_id, status`
