# 0002: Structured-First Memory

Date: 2026-05-04

Status: approved

## Context

The bot needs to remember meals, macros, weight, measurements, workouts, preferences, photos, progress, equipment, plans, and summaries. It should feel personal without relying on messy full-chat memory for normal answers.

## Decision

Use structured fitness data as the source of truth. Store queryable rows for meals, workouts, measurements, summaries, equipment, plates, reminders, plans, and preferences.

Maintain a compact AI-written profile summary for stable context. Store raw messages and photo metadata as audit history for debugging and future reprocessing, but do not load raw history into normal answers unless the user asks.

## Consequences

Summaries, trends, deletes, exports, and planning are more reliable. The profile summary keeps replies personal while controlling token cost. Raw audit data remains available without becoming the bot's default memory.

This requires careful schema design, user ID filtering, and retrieval rules.

Related docs: `docs/plans/02-data-memory.md`.
