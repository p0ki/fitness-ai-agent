# Fitness AI Agent

Personal Telegram fitness AI agent for a single authorized user.

Phase 1 is a Dockerized Python 3.11 Telegram polling bot. It uses no webhooks, exposed ports, reverse proxy, or public domain. Data lives under `/data` inside the container and `./data` on the host.

## Portfolio Highlights

- Docker-first Python 3.11 monolith with Telegram polling and no exposed ports.
- SQLite structured memory for profile, settings, logs, summaries, photo metadata, exports, backups, and soft deletes.
- Privacy-first allowlist gate that ignores unauthorized users before database writes, photo handling, or OpenAI calls.
- Centralized OpenAI boundary for text extraction and vision analysis, with graceful no-key fallbacks.
- Food-photo and progress-photo flows use temporary downloads only; Phase 1 does not permanently store image files.

## Architecture

- Python 3.11 application in one Docker container.
- Telegram polling bot; no webhook server, public domain, reverse proxy, or inbound port.
- SQLite database at `/data/fitness.db` in Docker and `./data` on the host.
- Runtime secrets are loaded from `.env`, which must stay private.
- OpenAI calls are centralized behind `app/openai_client.py`.

## Requirements

- Docker Desktop
- Git
- Telegram account
- BotFather bot token

## Windows Development

Create your environment file in PowerShell:

```powershell
copy .env.example .env
```

Or in Git Bash:

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```env
TELEGRAM_BOT_TOKEN=
ALLOWED_TELEGRAM_USER_IDS=
```

`OPENAI_API_KEY` is optional for text-only logging.
Food-photo and progress-photo analysis use OpenAI vision when `OPENAI_API_KEY`
is set. If it is missing, the bot fails gracefully, saves failed photo metadata
for authorized users, and gives a manual fallback.

Build and start:

```powershell
docker compose up -d --build
```

View logs:

```powershell
docker logs -f fitness-ai-agent
```

Stop:

```powershell
docker compose down
```

## Telegram Setup

1. Message `@BotFather` in Telegram.
2. Run `/newbot`.
3. Choose the bot name and username.
4. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.
5. Start a chat with your bot.
6. Send `/start`.
7. Send `/help` to confirm commands are working.

To discover your Telegram user ID for `ALLOWED_TELEGRAM_USER_IDS`, use one of these:

- message `@userinfobot` and copy the numeric ID
- during local development, leave `ALLOWED_TELEGRAM_USER_IDS` empty only to test access, then use a known numeric ID before real use

Before real use, set `ALLOWED_TELEGRAM_USER_IDS` to a comma-separated list of approved numeric IDs:

```env
ALLOWED_TELEGRAM_USER_IDS=<YOUR_TELEGRAM_USER_ID>
```

If the allowlist is empty, the bot allows development access. Use that only for local testing; do not leave it empty for real deployment.

## Safety

- `.env` and runtime data are private and should not be committed.
- Backups and exports are created under `/data/backups/` and `/data/exports/`; keep them private.
- Food and progress photos are temporary downloads only. Phase 1 does not permanently store image files.
- AI estimates and progress-photo feedback are not medical advice.

## Demo Limitations

There is no public hosted demo because this is designed as a private polling bot.
Real Telegram use and real photo analysis require private credentials in `.env`.

## Docker Validation

```powershell
docker compose build
docker compose up -d
docker logs -f fitness-ai-agent
docker compose down
```

## Troubleshooting

Bot does not reply:
- check that Docker Desktop is running
- check logs with `docker logs -f fitness-ai-agent`
- confirm you sent `/start` to the correct bot
- confirm `docker-compose.yml` exposes no ports; Telegram polling does not need ports

Invalid or missing `TELEGRAM_BOT_TOKEN`:
- verify the token from `@BotFather`
- confirm it is saved in `.env`

`OPENAI_API_KEY`:
- optional for text-only use
- required for real food-photo and progress-photo analysis

`OPENAI_VISION_MODEL`:
- optional; defaults to `gpt-4.1`

`ALLOWED_TELEGRAM_USER_IDS` mismatch:
- confirm the value is your numeric Telegram user ID
- during local development, leave it empty briefly to test access

## Available Commands

- `/start`
- `/help`
- `/profile`
- `/memory`
- `/data_summary`
- `/log_weight 80.0`
- `/log_measurement waist 88 cm`
- `/log_meal 3 eggs and tuna`
- `/log_workout 30 min bike`
- `/summary_today`
- `/summary_week`
- `/privacy`
- `/export`
- `/backup`
- `/delete_last`
- `/delete_today`
- `/delete_range 2026-05-01 2026-05-07`
- `/delete_all_data`
- `/cancel`
- send a photo with a clear food caption for a meal estimate and confirmation
- send a photo with a clear progress/body/front/side/back caption for progress analysis

Natural text examples also work for the basics:

- `weighed 80.0`
- `ate 3 eggs and tuna`
- `did 30 min bike`

## Current Capabilities

The app initializes the local SQLite database and stores profile, settings,
curated memories, raw message audit history, meals, workouts, body
measurements, deterministic daily/weekly summaries, food-photo metadata,
pending meal estimates, progress-photo metadata, and pending confirmation
actions for authorized users.

Privacy/admin tools can export active structured data, create local SQLite
backups, and soft-delete records after exact confirmation phrases. `/delete_all_data`
is implemented as a user-scoped soft delete.

Food and progress photos are temporarily downloaded for analysis and then
deleted. Phase 1 does not permanently store actual image files or temp paths.
Progress-photo body-fat estimates are rough visual-only metadata, not real
measurements, and are not written to body measurements.

## Not Medical Advice

AI estimates and progress-photo feedback are for personal tracking only. They
are not medical advice, diagnosis, treatment, or a professional fitness
assessment.

If a photo caption is missing or unclear, the bot asks:
`Is this food, progress, or ignore?`

Planned work includes equipment, planning, and reminders.
