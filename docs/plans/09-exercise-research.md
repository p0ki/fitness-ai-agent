# Exercise Research And Tutorial Stubs

## Phase 1 Scope

Phase 1 includes an interface and useful local fallback, not full web integration.

`app/research.py` should define the boundary for:

- exercise tutorial lookup
- exercise alternatives
- web search later
- YouTube lookup later
- PubMed/NCBI lookup later
- Reddit/forum lookup later
- source quality labeling later

No research code should live in Telegram handlers or planner internals.

## Commands

Phase 1:

- `/alternative`
- `/tutorial`
- `/dislike_exercise`
- `/like_exercise`
- `/cant_do`

Future:

- `/exercise_search`
- `/update_exercise_library`
- `/refresh_research`
- `/save_exercise`

## Tutorial Fallback

If no real YouTube API is configured, `/tutorial` should still be useful. It should return:

- suggested YouTube search query
- key form cues
- common mistakes
- safety notes
- equipment version

Example search query:

```text
beginner dumbbell Romanian deadlift tutorial proper form
```

## Alternatives

Alternative selection should preserve:

- movement pattern
- target muscles
- available equipment
- difficulty
- pain/dislike/cannot-do status
- load availability
- home setup

Movement patterns include squat, hinge, horizontal push, vertical push, horizontal pull, vertical pull, lunge/single-leg, carry, core anti-extension, core rotation, mobility, and cardio.

## Future Research Behavior

When enabled and explicitly requested, the bot can search current sources. It should summarize practical advice, not dump raw results.

Source priority:

1. reputable coaching or physiotherapy-style sources
2. scientific/research sources
3. video tutorials
4. Reddit/forums as anecdotal experience
5. general web only if useful

The bot must separate evidence-based information, coaching opinion, tutorial recommendations, and anecdotal forum input. Reddit/forums are not scientific proof.

When importing or suggesting exercises from search, the bot should check equipment requirements, goal fit, preferences, painful/cannot-do conflicts, form cues, common mistakes, and source quality. Ask before saving new exercises to the local library when appropriate.

## Future Tables

`research_cache` can store query, topic, source type, result JSON, summary, source links, quality labels, created/updated timestamps, and expiration.

Phase 1 can include the table in roadmap only unless a research feature needs it.

## Validation

Validate local alternatives, tutorial fallback text, preferences, equipment filtering, source field support, and no external API calls.
