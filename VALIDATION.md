# Validation

## Public offline regression tests

The public repository includes focused workout-parser tests using Python's
standard library. Run from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

These tests require no installed application dependencies, credentials, database,
or running bot. They cover whole-minute durations, range limits, command/natural
text parsing, and rejection of fractional-number suffixes. They do not replace
the full historical private suite or validate live integrations.

## Historical release validation

This release was prepared after validation with mocked Telegram and OpenAI integrations.

Before publication:

- Automated suite passed with 206 checks in private validation.
- Docker image build passed.
- Docker image test run passed with 206 tests.
- Container startup without `TELEGRAM_BOT_TOKEN` failed clearly with a required-token error.

Manual Telegram and real OpenAI vision checks require private credentials in `.env`.
