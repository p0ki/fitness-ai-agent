# Architecture

## Decision

Use a Docker-first Python monolith in Phase 1: one container, one Telegram polling process, one SQLite database, and one scheduler inside the bot process.

Runtime flow:

```text
Telegram update
-> allowlist auth gate
-> handler
-> service module
-> SQLite
-> OpenAI/planner/photo/research if needed
-> Telegram reply
```

## Module Boundaries

Target modules:

- `app/main.py`: startup, lifecycle, polling, scheduler wiring
- `app/config.py`: environment variables and settings
- `app/handlers.py`: Telegram routing and thin handlers
- `app/database.py`: SQLite connection, schema init, migrations, helpers
- `app/memory.py`: profile summary, memories, retrieval
- `app/openai_client.py`: OpenAI calls, prompts, structured output parsing
- `app/photos.py`: food/progress photo handling and temp cleanup
- `app/planner.py`: workout, stretch, meditation, recovery, summaries
- `app/equipment.py`: equipment, plates, load helpers, alternatives
- `app/reminders.py`: APScheduler jobs and reminder messages
- `app/research.py`: research/search interface and Phase 1 stubs
- `app/admin.py`: privacy, export, backup, deletes, data summary
- `app/utils.py`: shared helpers for dates, formatting, validation

Handlers must stay thin. They receive updates, check auth, parse basic input, call services, and send replies. They must not contain complex SQL, prompts, photo analysis, workout planning, admin logic, or scheduler logic.

## OpenAI And Research Boundaries

All OpenAI work goes through `app/openai_client.py`. Model names, prompts, retries, structured JSON validation, and fallback behavior stay centralized.

Research/search stays behind `app/research.py`. Phase 1 may provide stubs and tutorial search-query fallbacks. Phase 2 can add OpenAI web search, YouTube Data API, PubMed/NCBI, Reddit API, and source quality labels.

## Deployment Portability

The first real deployment target is Unraid, but Python code must not hardcode Unraid, Windows, Linode, IP addresses, domains, or host paths. Use `DATABASE_PATH`, default `/data/fitness.db`, and Docker volume mapping for persistence.

## No Overengineering Rule

Phase 1 intentionally avoids FastAPI, a web dashboard, webhook mode, reverse proxy, multiple containers, background workers, Redis, PostgreSQL, Kubernetes, and custom auth beyond Telegram allowed user IDs.

## Startup Logging

The app should log config loaded, database path, database initialized, Telegram polling starting, scheduler started, reminders loaded, and allowlist mode. Never log secrets.
