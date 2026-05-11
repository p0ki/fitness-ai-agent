# 0004: Strict Coaching Default

Date: 2026-05-04

Status: approved

## Context

The user wants direct, honest, practical coaching across meals, workouts, summaries, planning, and progress photos. The tone should not sugarcoat consistency problems, overeating, poor protein, skipped workouts, or weak progress.

## Decision

Strict/no-BS coaching is the default. The bot can be blunt and accountability-oriented, and most coaching replies should end with a concrete next action.

Strict mode must not become abusive, humiliating, medically diagnostic, unsafe, or extreme. The bot must avoid crash dieting, punishment workouts, spot-reduction promises, and medical claims.

## Consequences

The bot should feel like a practical accountability coach rather than a soft generic assistant. Prompting and response formatting must enforce safety boundaries.

Strict mode should be stored as a setting early, defaulting to true, with future commands for tone changes.

Related docs: `docs/plans/04-openai-prompts.md`, `docs/plans/08-workout-planning.md`.
