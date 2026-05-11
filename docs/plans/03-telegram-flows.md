# Telegram Commands And Flows

## Guardrail

Every update follows:

```text
Telegram update
-> check ALLOWED_TELEGRAM_USER_IDS
-> if unauthorized, silently ignore
-> no database write
-> no OpenAI call
```

If the allowlist is empty, development access can be open. Real deployment should set the allowlist.

## Command Groups

Start/help:

- `/start`
- `/help`

Profile and memory:

- `/profile`
- `/memory`
- `/forget` later

Logging:

- `/log_weight`
- `/log_meal`
- `/log_workout`
- `/log_measurement`

Summaries and planning:

- `/summary_today`
- `/summary_week`
- `/plan_tomorrow`
- `/workout_today`

Recovery:

- `/stretch`
- `/meditation`
- `/recovery`

Workout status:

- `/done`
- `/skip_workout`

Photos:

- photo handler
- `/progress`
- `/reprocess_last_photo` later

Equipment and plates:

- `/equipment`
- `/add_equipment`
- `/remove_equipment`
- `/equipment_setup`
- `/plates`
- `/add_plate`
- `/remove_plate`
- `/update_plate`
- `/max_load`

Exercise preferences and stubs:

- `/alternative`
- `/tutorial`
- `/dislike_exercise`
- `/like_exercise`
- `/cant_do`

Privacy and admin:

- `/privacy`
- `/data_summary`
- `/export`
- `/backup`
- `/delete_last`
- `/delete_today`
- `/delete_range`
- `/delete_all_data`
- `/cancel`

Reminders:

- `/reminders`
- `/reminders_on`
- `/reminders_off`

Tone:

- `/strict_mode_on`
- `/strict_mode_off`
- `/tone` later

## Natural Language

The bot should classify normal text into intents: meal, weight, measurement, workout, planning, summary, equipment update, plate update, exercise preference, general fitness question, or unclear chat.

High confidence can act directly. Medium confidence can act and summarize with correction option. Low confidence asks one concise clarification.

Metric units are default. The bot should parse comma decimals like `76,4 kg` and `2x2,5kg`.

## Confirmation State

Use `/cancel` to cancel pending meal confirmations, delete confirmations, equipment setup, reminder setup, or any multi-step state.

Important confirmations should persist in SQLite where needed. Dangerous delete confirmations expire after about 10-15 minutes and require exact phrases.

Food confirmations can be flexible: yes, save, log it, edit, no, cancel.

## Reply Style

Telegram replies should be concise, readable, and sectioned. Avoid giant paragraphs and brittle tables. Use short headings, bullets, clear numbers, and a next action.

If a plan or summary is long, send a short version first or split messages.
