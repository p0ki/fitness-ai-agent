# 0007: Centralized OpenAI Calls

Date: 2026-05-04

Status: approved

## Context

The bot uses OpenAI for classification, extraction, food photos, progress photos, summaries, planning, memory extraction, and future research summaries. Scattered API calls would make testing, retries, model changes, and safety harder.

## Decision

All OpenAI calls go through `app/openai_client.py`. Handlers and service modules do not call OpenAI directly.

"Do not call OpenAI directly" means no OpenAI SDK/API usage outside `app/openai_client.py`. Service modules may call wrapper functions from `app/openai_client.py`.

Use structured outputs where possible for data that can affect persistence. Validate AI output before saving. Model names should be centralized in config.

## Consequences

The code is easier to test with fake clients. Prompt changes and model upgrades are localized. The app can enforce malformed JSON fallback, confidence handling, and safety boundaries consistently.

Related docs: `docs/plans/04-openai-prompts.md`.
