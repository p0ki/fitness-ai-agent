# OpenAI Prompts And AI Behavior

## Boundary

All OpenAI calls go through `app/openai_client.py`. Handlers and service modules never call OpenAI directly.

"Do not call OpenAI directly" means do not use the OpenAI SDK outside `app/openai_client.py`. Service modules may call wrapper functions from `app/openai_client.py`.

The wrapper should expose clear functions:

- `classify_intent()`
- `extract_structured_log()`
- `analyze_food_photo()`
- `analyze_progress_photo()`
- `generate_daily_summary()`
- `generate_weekly_summary()`
- `generate_workout_plan()`
- `generate_stretch_plan()`
- `generate_meditation_plan()`
- `extract_memories()`
- `update_profile_summary()`
- `generate_general_reply()`
- `summarize_research_results()` later

Model names should be config-driven. For Phase 1, config-driven can mean defaults in `config.py` with optional environment overrides later. Model env vars are not required in `.env.example` until needed. Prompt constants can live in `openai_client.py` first and move to `app/prompts.py` if they become large.

## Structured Outputs

Any AI result that can affect database records should use strict JSON schemas where possible. Validate required keys, enum values, numeric ranges, confidence, and safety constraints.

AI returns suggestions, estimates, classifications, and drafts. The app decides whether to save, ask confirmation, choose source labels, or reject low-confidence output. AI never writes database rows directly.

Malformed structured output gets one retry or repair attempt. If still invalid, use a safe fallback or ask for clarification. Never save malformed AI output.

## Confidence

Use confidence values low, medium, and high for:

- intent classification
- food photo analysis
- meal estimates
- progress photo visual estimates
- exercise classification
- memory extraction where useful

Low confidence should trigger clarification or prevent silent saving of important data.

## Coaching Tone

Strict/no-BS is default. The bot may be direct about overeating, poor protein, missed workouts, low consistency, sweets, and weak progress. It must not be abusive, humiliating, medically diagnostic, or unsafe.

Most coaching replies should end with a concrete next action.

## Safety Boundaries

The bot must not diagnose medical conditions. For sharp pain, injury, chest pain, dizziness, fainting, severe symptoms, medications, medical conditions, or eating-disorder behavior, it should keep advice general and recommend professional help when appropriate.

No spot-reduction promises. No crash dieting, starvation, unsafe dehydration, purging, compensatory behavior, punishment workouts, or maxing out without experience.

## Cost Control

Do not send huge raw history to OpenAI. Retrieve compact profile summary, relevant structured data, and short recent context. Use vision only for photos. Use web search only when explicitly requested.

## Validation

Validation should mock OpenAI. Important cases include valid JSON parsing, malformed output fallback, low-confidence handling, safety filtering, and service behavior when AI fails.
