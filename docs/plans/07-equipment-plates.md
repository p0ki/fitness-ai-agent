# Equipment, Plates, And Exercise Preferences

## Purpose

The bot must plan workouts around equipment saved by the user. It should not suggest missing equipment, painful/cannot-do exercises, or loads that cannot be built with saved plates.

## Data Model

Use structured tables:

- `equipment`: actual user inventory such as free weights, barbell, bench, exercise mat
- `loadable_equipment`: barbell, dumbbell handles, EZ bar, loadable handles, weights, sleeve details, max load, quantity
- `weight_plates`: weight, quantity, hole diameter, plate type, compatibility, notes
- `exercise_preferences`: liked, disliked, cannot_do, painful, avoid, favorite
- `exercise_library`: seeded local exercise library

Separate reference equipment from user inventory. The reference library can know many equipment types exist, but only user inventory is considered available.

Unknown equipment details stay null or unknown and are filled through `/equipment_setup`.

## Commands

- `/equipment`
- `/add_equipment`
- `/remove_equipment`
- `/equipment_setup`
- `/plates`
- `/add_plate`
- `/remove_plate`
- `/update_plate`
- `/max_load`
- `/dislike_exercise`
- `/like_exercise`
- `/cant_do`
- `/alternative`
- `/tutorial`

`/equipment` should list inventory and missing details. `/plates` should group plate inventory, total plate weight, compatibility warnings, and next setup question.

`/equipment_setup` asks one question at a time and supports `/cancel`.

## Plate Parsing

Support:

- `2x10kg`
- `2 x 10 kg`
- `4 plates 5kg`
- `4x5kg 30mm`
- `2x2.5kg`
- `2x2,5kg`
- `pair of 5kg plates`

Never allow negative inventory. Removing too many plates should produce a clear refusal.

## Load Rules

Keep Phase 1 conservative. Do not fake precision when bar weight, handle weight, sleeve diameter, compatibility, or max load are unknown.

Barbell total = empty bar + compatible plates loaded symmetrically.

Dumbbell total = handle + plates on both sides of one dumbbell. Paired dumbbell exercises require symmetric loading across both handles.

If exact target load is impossible, choose nearest available below target unless recent logs justify higher. Phase 1 `/max_load` can be approximate and list missing info.

## Seeded Exercise Library

Seed roughly 50-100 practical beginner/intermediate movements across warm-up, bodyweight, dumbbell, barbell, bench, core, stretching, mobility, cardio, and breathing.

Seeded exercises should have `source_type=seed`, `source_quality=high` or `medium`, and `verified=true`.

Painful exercises are stricter than disliked exercises. Do not push through pain or diagnose it. Offer pain-free alternatives and professional help if pain persists.

## Testing

Test parser formats, comma decimals, invalid input, no negative inventory, soft delete, user isolation, total plate weight, conservative load helpers, missing detail messages, seeded library existence, source fields, preferences, and planner avoidance behavior.
