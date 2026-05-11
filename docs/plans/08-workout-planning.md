# Workout Planning, Stretching, Meditation, And Recovery

## Purpose

Plans should be complete, realistic, and actionable. They use structured context: profile summary, goals, recent logs, workout history, equipment, plates, exercise preferences, limitations, seeded exercises, and strict mode.

## Phase 1 Commands

- `/plan_tomorrow`
- `/workout_today`
- `/stretch`
- `/meditation`
- `/recovery`
- `/done`
- `/skip_workout`

## Plan Shape

Every full plan should include:

- goal of the day
- warm-up, 5-10 minutes
- strength block with exercises, sets, reps, rest, and load guidance
- cardio/conditioning
- core if useful
- stretching/cooldown, 5-10 minutes
- breathing/meditation, 3-10 minutes
- nutrition reminder if relevant
- alternatives
- done criteria
- no-BS next action

Default full plan duration is 45-60 minutes. Also support short 20-30 minutes, minimum viable 10-15 minutes, and recovery 10-25 minutes.

Default intensity is moderate unless recent logs or user input suggest easy, hard, or recovery.

## Weekly Balance

Phase 1 uses simple split awareness:

- full-body strength
- upper body
- lower body
- cardio/recovery
- mobility/stretch

For fat loss and better fitness, default toward full-body strength about three times per week, walking/cycling/cardio on other days, regular core and mobility, and recovery when needed.

Avoid repeating the same hard muscle group on consecutive days when recent logs show it.

## Load And Progression

Use exact loads only when equipment and plates are known. Otherwise use RPE/RIR:

- easy: 3-4 reps in reserve
- moderate: 1-3 reps in reserve
- hard: 0-1 reps in reserve, no form breakdown

No maxing out in Phase 1.

Progression should be conservative: add reps, one set, small available load, slower tempo, shorter rest, better range of motion, or more walking/cardio duration.

## Safety

Avoid painful/cannot-do exercises. Avoid disliked exercises when good alternatives exist. Do not promise belly-fat spot reduction. Do not use punishment workouts for overeating. Stop or modify for sharp pain and recommend professional help for persistent or serious symptoms.

Meditation/breathing is practical: relaxation, stress reset, sleep wind-down, cooldown, or focus. It must not claim to cure medical or mental health conditions.

## Storage

Use `workout_plans` with flexible JSON/text:

- `plan_type`
- `local_date`
- `estimated_duration_minutes`
- `intensity`
- `plan_json`
- `plan_text`
- `status`
- `completed_at_utc`
- `skipped_reason`

`/done` marks an active plan complete and creates or links a `workouts` row with `source=generated_plan_done`. `/skip_workout` saves a reason and offers a minimum fallback. If no active plan exists, respond with a manual logging option.

## Testing

Mock plan generation. Test required JSON fields, plan save, plan text, equipment/preference filters, impossible loads, no-plan behavior, duplicate/replace behavior, `/done`, `/skip_workout`, user isolation, and standalone stretch/meditation/recovery safety.
