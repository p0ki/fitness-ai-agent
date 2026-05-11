# Food Photos

## Default Flow

Food photos use confirmation by default because image calorie estimates can be wrong.

1. Authorized user sends a photo.
2. The bot downloads a suitable Telegram photo size temporarily.
3. `app/photos.py` calls `openai_client.analyze_food_photo()`.
4. Temporary file cleanup runs in `try/finally`.
5. Store `photo_logs` metadata and AI analysis.
6. Create `pending_meal_estimates`.
7. Reply with food estimate, macros, confidence, uncertainty, and confirmation options.
8. Save to `meals` only after confirmation, correction, or explicit fast-log caption.

Do not store the temporary local path. Phase 1 always stores `stored_locally=false` and `local_path=null`.

## Reply Format

Example:

```text
Food estimate:
- likely: eggs, tuna, tomatoes, paprika
- calories: ~520 kcal
- protein: ~55g
- carbs: ~15g
- fat: ~27g
- fiber: ~4g
Confidence: medium

Assumptions:
I cannot see exact oil or portion size.

Save this meal?
Reply:
yes / edit: ... / no
```

Low-confidence estimates should ask for correction before saving and make uncertainty obvious.

## Confirmation And Correction

Accepted low-risk confirmations include yes, save, log it, edit, no, cancel, and `/cancel`.

Pending estimates have statuses: pending, confirmed, corrected, cancelled, expired. They should expire after about 24 hours. Duplicate confirmations should not create duplicate meals.

If no pending meal exists and the user replies yes, say no pending meal was found.

Corrections preserve the original AI estimate in `photo_logs` or `pending_meal_estimates`; final accepted values go to `meals`.

## Fast Path

If the caption clearly says `log this meal`, `save this meal`, `track this`, `this is my lunch`, `this is my dinner`, or similar, the bot may save immediately. It must still say it saved an estimate, include confidence, and explain how to correct it.

## Ambiguous Photos

If the bot cannot classify a photo, ask whether it is food, progress, equipment, or ignore. Do not automatically save ambiguous photos as meals.

## Tables

`photo_logs` stores Telegram message/file IDs, type, caption, AI description, analysis JSON, confidence, linked record, timestamps, and soft-delete fields.

`pending_meal_estimates` stores estimate JSON, calories, protein, carbs, fat, fiber, confidence, status, expiration, and links.

`meals` stores confirmed or explicitly logged values only.

## Testing

Mock Telegram downloads and OpenAI vision. Test pending creation, yes confirmation, correction, cancel, fast path, duplicate confirmation, no pending meal, temp cleanup on success/failure, and OpenAI failure without final meal save.
