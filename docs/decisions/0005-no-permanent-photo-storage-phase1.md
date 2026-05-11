# 0005: No Permanent Photo Storage In Phase 1

Date: 2026-05-04

Status: approved

## Context

The bot will process food and progress photos. Photos are sensitive, especially progress photos. Food estimates are useful but uncertain.

## Decision

Phase 1 does not permanently store actual image files. The bot may temporarily download Telegram photos for OpenAI vision analysis, but temporary files must be deleted after analysis with `try/finally`.

Store only Telegram file IDs, metadata, captions, AI descriptions, estimates, confidence, and linked structured record IDs.

## Consequences

Privacy risk is lower and Unraid storage is simpler. Future local photo storage remains possible, but only after explicit approval.

The app must not store temp file paths in the database. `stored_locally=false` and `local_path=null` are the Phase 1 defaults.

Related docs: `docs/plans/05-food-photos.md`, `docs/plans/06-progress-photos.md`.
