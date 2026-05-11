# Backlog

## Phase 2

Research and exercise enrichment:

- real OpenAI web search integration
- YouTube Data API tutorial lookup
- PubMed/NCBI research search
- Reddit API for anecdotal equipment/exercise discussions
- `research_cache`
- source quality labels
- `/exercise_search`
- `/save_exercise`
- `/refresh_exercise`
- richer exercise library enrichment

Training analytics:

- weekly training plan builder
- `workout_exercises`
- `workout_sets`
- personal records
- progression tracking
- volume tracking
- deload logic
- readiness scoring
- advanced periodization

Reminders:

- `/set_reminder`
- snooze
- quiet hours
- workday/weekend schedules
- missed-log nudges
- automatic daily summaries
- automatic weekly summaries

Photos:

- optional local photo storage after explicit approval
- progress photo comparison improvements
- equipment photo identification
- plate photo label reading

Exports and visualization:

- CSV exports
- Google Sheets export
- charts
- dashboard, see Dashboard And Wearable Sync

## Dashboard And Wearable Sync

### Phase 2/3 Dashboard

Build a private local dashboard for Unraid.

Possible stack:

- Streamlit first for speed
- FastAPI + React later if needed

Dashboard should show:

- weight trend
- waist trend
- calories and protein
- meals
- workouts
- walking/cardio
- reminders
- equipment and plates
- workout plans
- skipped workouts
- progress-photo timeline
- weekly summaries

Dashboard security rule:

Dashboard must be private-only. If exposed beyond localhost or the Unraid LAN later, it needs authentication.

### Samsung Galaxy Fit3 / Samsung Health Sync

Preferred path:

Galaxy Fit3 -> Samsung Health -> Health Connect -> companion app/export -> fitness-ai-agent.

Possible sync options:

1. Manual Samsung Health export/import first.
2. Android companion app reading Health Connect later.
3. Samsung Health Data SDK only if access/partnership is practical.
4. Third-party sync apps as bridge if useful.

Future wearable tables:

- `daily_activity`
- `sleep_logs`
- `heart_rate_logs`
- `wearable_workouts`
- `wearable_sync_sources`

Privacy rule:

Wearable sync must be opt-in. Do not sync health data without explicit user approval. Imported wearable data must follow the same export/delete/privacy rules as other stored data.

Do not add this to Phase 1 implementation.

Phase 1 should only prepare the database so future wearable data can be stored.

## Phase 3

Deployment and product extensions:

- Linode deployment refinement
- published Docker image
- GitHub Container Registry or Docker Hub
- Unraid custom Docker template
- optional dashboard with auth
- advanced backup/restore tooling
- multi-user hardening if ever needed

## Product Ideas

- habit streaks
- sleep/recovery tracking
- soreness tracking
- snack strategy library
- high-protein dessert ideas
- grocery list generation
- meal prep planning
- cycling/running history
- dog-walk cardio tracking
- waist trend reports
- monthly progress review

## Rules For Backlog Items

Backlog items are not Phase 1 commitments until they are promoted into the roadmap. New features should preserve privacy, structured-first memory, and Docker portability.
