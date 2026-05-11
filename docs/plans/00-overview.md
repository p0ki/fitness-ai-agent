# Overview

## Vision

The fitness AI agent is a personal Telegram coach for a single authorized user. It should help track body weight, measurements, meals, macros, workouts, progress photos, equipment, plates, preferences, reminders, and planning. The product should feel practical, direct, and useful every day, not like a vague chatbot.

The bot runs in a private one-to-one Telegram chat. It is command-friendly but natural-language-first, so messages like `weighed 80.0`, `ate tofu rice bowl`, `did 30 min bike`, or `plan tomorrow short` should work alongside explicit commands.

## Primary Goals

- User-defined body, nutrition, and training goals
- Better fitness and consistency over configurable time horizons
- Practical meal and macro tracking
- Configurable preferences and constraints
- Home or gym training based on saved equipment
- Daily and weekly feedback with strict/no-BS coaching
- Docker deployment on Windows first and Unraid second

## Phase 1 Product Scope

Phase 1 includes the major product foundations:

- Telegram polling bot
- allowlist access control
- SQLite structured memory
- raw audit history
- compact profile summary
- text logging for meals, weight, measurements, and workouts
- food photo analysis with confirmation
- progress photo analysis with strict feedback
- privacy, export, backup, and delete tools
- equipment and plate inventory
- seeded exercise library
- workout, stretch, meditation, and recovery planning
- exercise alternatives and tutorial fallback
- simple scheduled reminders
- Windows and Unraid Docker documentation

## What Phase 1 Avoids

Phase 1 does not include a web dashboard, Telegram webhook mode, exposed ports, reverse proxy, PostgreSQL, Redis, multi-container architecture, background worker container, Kubernetes, public API, or permanent photo storage.

## Future Scope

Phase 2 and beyond can add real web search, YouTube API, PubMed/NCBI, Reddit API, research cache, progress charts, Google Sheets export, optional local photo storage, advanced scheduling, dashboards, progression analytics, and Linode deployment refinement.
