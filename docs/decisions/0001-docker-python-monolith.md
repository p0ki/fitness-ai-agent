# 0001: Docker Python Monolith

Date: 2026-05-04

Status: approved

## Context

The bot is designed for local Docker development and private deployment, with Unraid as the first home-server target. It needs Telegram polling, SQLite persistence, OpenAI calls, reminders, and privacy/admin tools. The design should remain portable to a small VPS later, but Phase 1 avoids public webhooks and exposed network ports.

## Decision

Use one Docker container running one Python 3.11 Telegram polling process. SQLite is stored at `/data/fitness.db`. The same process owns Telegram polling, app services, database access, OpenAI calls, and APScheduler reminders.

Do not use a web server, webhook, reverse proxy, Redis, PostgreSQL, queue, separate worker, or multi-container architecture in Phase 1.

## Consequences

Deployment is simple on Windows and Unraid. Polling avoids public ports, HTTPS, domains, and router changes. SQLite and a mounted `/data` directory are enough for a personal bot.

The app must keep module boundaries clean so the monolith does not become tangled. If future scale requires a worker, dashboard, or PostgreSQL, those can be added after Phase 1 works.

Related docs: `docs/plans/01-architecture.md`, `docs/plans/12-devops-unraid.md`.
