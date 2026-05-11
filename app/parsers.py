from __future__ import annotations

from dataclasses import dataclass
import re


VALID_CONFIDENCE = {"low", "medium", "high"}


@dataclass(frozen=True)
class ParsedMeasurement:
    measurement_type: str
    value: float
    unit: str
    source: str
    notes: str | None = None


@dataclass(frozen=True)
class ParsedMeal:
    description: str
    calories_estimate: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    confidence: str
    source: str
    notes: str | None = None


@dataclass(frozen=True)
class ParsedWorkout:
    workout_type: str
    summary: str
    duration_minutes: int | None
    intensity: str | None
    source: str
    notes: str | None = None


def parse_weight(text: str) -> ParsedMeasurement:
    source = _source_for(text)
    body = _strip_command(text, "/log_weight")
    match = re.search(r"(?<!\w)(-?\d+(?:[\.,]\d+)?)(?:\s*kg)?\b", body, re.I)
    if match is None:
        raise ValueError("Could not find a weight in kg.")

    value = _parse_decimal(match.group(1))
    if value < 20 or value > 350:
        raise ValueError("Weight value is outside the supported range.")

    return ParsedMeasurement(
        measurement_type="weight",
        value=value,
        unit="kg",
        source=source,
    )


def parse_measurement(text: str) -> ParsedMeasurement:
    source = _source_for(text)
    body = _strip_command(text, "/log_measurement")
    match = re.search(
        r"^(?P<kind>[^\d-]+?)\s+(?P<value>-?\d+(?:[\.,]\d+)?)\s*(?P<unit>cm|kg|mm)?$",
        body,
        re.I,
    )
    if match is None:
        raise ValueError("Use a measurement like: waist 88 cm.")

    value = _parse_decimal(match.group("value"))
    if value <= 0 or value > 300:
        raise ValueError("Measurement value is outside the supported range.")

    kind = _normalize_spaces(match.group("kind")).lower()
    if not kind:
        raise ValueError("Measurement type is required.")

    return ParsedMeasurement(
        measurement_type=kind,
        value=value,
        unit=(match.group("unit") or "cm").lower(),
        source=source,
    )


def parse_workout(text: str) -> ParsedWorkout:
    source = _source_for(text)
    body = _strip_command(text, "/log_workout")
    body = _strip_prefix(body, ("did", "completed", "finished"))
    match = re.search(r"(?P<duration>-?\d+)\s*(?:min|mins|minute|minutes)\b", body, re.I)
    if match is None:
        raise ValueError("Use a workout like: 30 min bike.")

    duration = int(match.group("duration"))
    if duration <= 0 or duration > 600:
        raise ValueError("Workout duration is outside the supported range.")

    rest = body[match.end() :].strip(" -:,.")
    workout_type = _normalize_spaces(rest).lower() if rest else "workout"
    summary = _normalize_spaces(
        f"{duration} min {rest}".strip() if rest else f"{duration} min workout"
    )

    return ParsedWorkout(
        workout_type=workout_type,
        summary=summary,
        duration_minutes=duration,
        intensity=None,
        source=source,
    )


def parse_meal(text: str) -> ParsedMeal:
    source = _source_for(text)
    body = _strip_command(text, "/log_meal")
    body = _strip_prefix(body, ("ate", "had", "logged", "log"))
    description = _normalize_spaces(body)
    if len(description) < 3:
        raise ValueError("Meal description is required.")

    return ParsedMeal(
        description=description,
        calories_estimate=None,
        protein_g=None,
        carbs_g=None,
        fat_g=None,
        fiber_g=None,
        confidence="low",
        source=source,
    )


def _source_for(text: str) -> str:
    if text.strip().startswith("/"):
        return "manual_command"
    return "natural_text"


def _strip_command(text: str, command: str) -> str:
    body = _normalize_spaces(text)
    if body.lower().startswith(command.lower()):
        body = body[len(command) :].strip()
    return body


def _strip_prefix(text: str, prefixes: tuple[str, ...]) -> str:
    body = _normalize_spaces(text)
    lower = body.lower()
    for prefix in prefixes:
        if lower == prefix:
            return ""
        if lower.startswith(f"{prefix} "):
            return body[len(prefix) :].strip()
    return body


def _parse_decimal(raw_value: str) -> float:
    return float(raw_value.replace(",", "."))


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())
