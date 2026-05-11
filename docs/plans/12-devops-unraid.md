# DevOps, Docker, Windows, And Unraid

## Runtime

Phase 1 runs:

- Python 3.11
- one Docker container
- Telegram polling mode
- no exposed ports
- no webhook
- no reverse proxy
- SQLite at `/data/fitness.db`
- persistent data through Docker volume
- secrets/config from `.env`

## Dockerfile

Use `python:3.11-slim`, `WORKDIR /app`, install `requirements.txt`, copy `app/`, create `/data`, and start with:

```text
python -m app.main
```

Use a non-root user if practical. If Unraid permissions become painful, document the chosen approach.

## Requirements

Expected Phase 1 dependencies:

- `python-telegram-bot`
- `openai`
- `python-dotenv`
- `APScheduler`

Optional only if useful: `pydantic`, `tzdata`, `requests`, or `httpx`.

Pin major package versions once the first working combination is verified. During early development, broad versions are acceptable, but before real Unraid deployment, freeze or pin known-good dependencies.

## Environment

`.env.example` should include exactly:

```env
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
DATABASE_PATH=/data/fitness.db
ALLOWED_TELEGRAM_USER_IDS=
TIMEZONE=UTC
REMINDERS_ENABLED=true
WEIGH_IN_REMINDER_TIME=07:30
MEAL_LOG_REMINDER_TIME=14:00
WORKOUT_REMINDER_TIME=18:00
DAILY_SUMMARY_REMINDER_TIME=21:00
WEEKLY_SUMMARY_DAY=sunday
WEEKLY_SUMMARY_REMINDER_TIME=19:00
```

Future optional model/search keys can be documented later.

## Git Ignore

`.gitignore` should include:

```gitignore
.env
*.env
data/*.db
data/*.sqlite
data/backups/
data/exports/
data/temp/
__pycache__/
*.pyc
.test-data/
.venv/
venv/
.DS_Store
Thumbs.db
```

Allow:

```text
data/.gitkeep
```

## Compose

Baseline:

```yaml
services:
  fitness-ai-agent:
    build: .
    container_name: fitness-ai-agent
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/data
```

No ports, reverse proxy labels, or network customization in Phase 1.

## Windows Flow

PowerShell first run:

```powershell
copy .env.example .env
docker compose up -d --build
docker logs -f fitness-ai-agent
docker compose down
```

## Unraid

Preferred early option: Docker Compose plugin.

Host layout:

```text
/mnt/user/appdata/fitness-ai-agent/
├─ data/
│  ├─ fitness.db
│  ├─ backups/
│  ├─ exports/
│  └─ temp/
├─ .env
└─ docker-compose.yml
```

Map:

```text
/mnt/user/appdata/fitness-ai-agent/data:/data
```

Backups live at `/mnt/user/appdata/fitness-ai-agent/data/backups/`. Exports live at `/mnt/user/appdata/fitness-ai-agent/data/exports/`. Include the data folder in the Unraid backup strategy.

## Operations

Logs:

```bash
docker logs -f fitness-ai-agent
```

Restart:

```bash
docker restart fitness-ai-agent
```

Update:

```bash
git pull
docker compose up -d --build
```

## Troubleshooting

Cover bot token, allowed user IDs, OpenAI key, database mount, permissions, scheduler settings, internet access, and Docker build failures in README.

Because polling is used, no router ports, HTTPS, domain, or reverse proxy are required.
