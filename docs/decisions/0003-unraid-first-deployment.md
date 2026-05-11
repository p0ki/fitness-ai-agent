# 0003: Unraid First Deployment

Date: 2026-05-04

Status: approved

## Context

The user develops on Windows and wants the first real deployment on an Unraid home server. Linode remains a possible later target. Telegram polling means no public endpoint is required.

## Decision

Target Windows Docker Desktop for development and Unraid for first real deployment. Keep all Python code portable by using environment variables and Docker volume mapping.

The database path is configured with `DATABASE_PATH`, default `/data/fitness.db`. On Unraid, `/data` maps to `/mnt/user/appdata/fitness-ai-agent/data`.

## Consequences

The bot can run privately at home without exposing ports, domains, reverse proxies, or HTTPS. Backups and exports live under the Unraid appdata data folder and should be included in the user's Unraid backup strategy.

Linode remains portable because no Unraid paths are hardcoded in code.

Related docs: `docs/plans/12-devops-unraid.md`.
