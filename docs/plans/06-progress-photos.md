# Progress Photos

## Phase 1 Behavior

Progress photos are analyzed temporarily and stored as metadata plus AI notes. Phase 1 does not permanently store actual image files.

Default flow:

1. Authorized user sends a likely progress photo.
2. The bot downloads it temporarily.
3. `app/photos.py` calls `openai_client.analyze_progress_photo()`.
4. Temporary cleanup runs in `try/finally`.
5. Store `photo_logs` metadata.
6. Create `progress_photos`.
7. Reply in strict/no-BS style.

If the caption clearly indicates food, keep the food-photo flow. If it clearly
indicates progress/body/front/side/back, use progress-photo analysis. If the
caption is missing or unclear, ask exactly: `Is this food, progress, or ignore?`
Do not create a progress record unless analysis validates a progress-photo type.

## Strict Feedback

The bot may directly mention visible belly/waist changes, softness, lack of definition, posture, comparison quality, lighting, pose differences, and consistency problems.

Allowed:

- rough visual body-fat estimate range
- direct progress comments
- practical next action
- warning that comparison conditions are bad

Not allowed:

- abuse or humiliation
- medical diagnosis
- disease, skin, mole, cancer, hormone, insulin, or gynecomastia claims
- exact body-fat or measurement claims as fact
- unsafe dieting
- punishment workouts

## Body Fat Estimate Rule

Visual estimates must be stored as visual-only:

- `visual_body_fat_estimate_range`
- `visual_body_fat_confidence`
- `estimate_type = visual_only`

They must not be saved as real measurements or medical records.

Example allowed: `Very rough visual estimate: maybe 22-27%. Confidence: low.`

## Comparison Behavior

If no previous progress photo exists, save as baseline and explain that future comparison needs standardization.

If previous records exist, comparison can be simple and cautious. Mention if lighting, pose, distance, clothing, or angle differ.

Recommended standardization:

- same location
- same lighting
- same time of day
- same distance
- same pose
- front, side, and back angles
- weekly or biweekly, not daily obsessive checking

## Table

`progress_photos` should store Telegram user/file IDs, `photo_log_id`, taken time, local date, angle, user note, AI description, comparison conditions JSON, visible notes, strict feedback, visual body-fat range/confidence, overall confidence, local storage fields, timestamps, and soft-delete fields.

## Testing

Mock photo and OpenAI. Test progress record creation, no local path, no permanent file storage, low-confidence visual estimate as estimate only, unclear photo clarification, safe wording filter, and temp cleanup on success/failure.
