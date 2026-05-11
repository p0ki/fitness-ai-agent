# Privacy And Admin Tools

## Principle

Data is local, transparent, exportable, backed up, and deletable. Privacy/admin tools are early Phase 1.

All privacy/admin logic belongs in `app/admin.py`. Handlers only parse commands, call admin services, and send replies.

## Commands

- `/privacy`
- `/data_summary`
- `/export`
- `/backup`
- `/delete_last`
- `/delete_today`
- `/delete_range`
- `/delete_all_data`
- `/cancel`

All commands are scoped to requesting `telegram_user_id`, except `/backup`, which creates a full SQLite database backup and is restricted to allowed users.

## Privacy Output

`/privacy` should mention:

- database: `/data/fitness.db` inside Docker
- secrets: `.env`
- no permanent photo storage in Phase 1
- temporary photo analysis and cleanup
- stored photo data: Telegram file ID, metadata, AI notes, estimates, confidence
- OpenAI for text and image analysis
- raw messages for audit/debugging, not normal memory
- `/export`, `/backup`, and delete commands

## Export

Default `/export` creates:

```text
/data/exports/fitness_export_<telegram_user_id>_<YYYYMMDD_HHMMSS>.json
```

Create the exports folder if missing. Use UTF-8 JSON. Include export version, exported time, telegram user ID, structured active data, settings, equipment, plans, progress/photo metadata, and no actual images or secrets.

Future modes can include `/export raw`, `/export no_raw`, and CSV files. Phase 1 default export excludes `raw_messages`. Raw message export can be added later as `/export raw`. This keeps normal exports cleaner and more privacy-friendly.

Try sending the export as a Telegram document if simple. If not, reply with the Docker path and Unraid host mapping.

## Backup

`/backup` creates:

```text
/data/backups/fitness_backup_<YYYYMMDD_HHMMSS>.db
```

Use SQLite backup API or `VACUUM INTO`, not plain copying of a live database. Do not automatically send the full DB over Telegram in Phase 1; reply with the local backup path.

## Delete Flows

Use previews and exact confirmation phrases:

- `/delete_last`: `YES DELETE`
- `/delete_today`: `CONFIRM DELETE TODAY`
- `/delete_range`: `CONFIRM DELETE RANGE`
- `/delete_all_data`: `CONFIRM DELETE ALL`

Do not accept vague confirmations for dangerous deletes.

Store pending confirmations in `pending_actions` with action type, payload JSON, phrase, status, creation, expiration, completion, and cancellation timestamps. Expire after about 10-15 minutes.

Use transactions. If delete fails, roll back and report honestly.

Prefer soft delete for normal commands. `/delete_all_data` can hard delete only if implemented safely; otherwise soft delete is acceptable and must be documented.

## Coverage

`/data_summary` shows active row counts by implemented table. Export/delete coverage must be documented and tested for user isolation.

## Testing

Test exact confirmations, wrong/expired confirmation no-ops, user isolation, export file structure, backup openability, soft-delete filtering, no secrets/images in export, transactions, and `.gitignore` manual checks.
