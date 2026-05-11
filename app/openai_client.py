from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from pathlib import Path
import re
from typing import Any


VALID_INTENTS = {"meal", "weight", "measurement", "workout", "unclear"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_UNITS = {"kg", "cm", "mm"}
VALID_MEASUREMENT_TYPES = {
    "weight",
    "waist",
    "bellybutton waist",
    "hips",
    "hip",
    "chest",
    "arm",
    "leg",
    "measurement",
}
NON_NEGATIVE_FIELDS = {
    "calories_estimate",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
}
DEFAULT_FOOD_PHOTO_PROMPT = """
Analyze this as a food photo for personal nutrition logging.
Return JSON only with:
photo_type: food, other, or unknown
ai_description: short visual description
detected_foods: array of foods
portion_assumptions: array of assumptions
calories_estimate, protein_g, carbs_g, fat_g, fiber_g: numbers or null
confidence: low, medium, or high
uncertainty_notes: array of uncertainty notes
needs_confirmation: boolean
suggested_user_question: short question or null

Rules:
- Estimates are rough, not exact.
- If this is not clearly food, use photo_type other or unknown.
- Do not make medical claims.
"""
DEFAULT_PROGRESS_PHOTO_PROMPT = """
Analyze this as a fitness progress photo for personal progress tracking.
Return JSON only with:
photo_type: progress, food, other, or unknown
angle: front, side, back, or unknown
ai_description: short visual description
visible_notes: array of visible non-medical observations
comparison_conditions: object describing lighting, pose, distance, clothing, angle, timing
strict_feedback: direct but safe coaching feedback
visual_body_fat_estimate_range: rough visual-only range text or null
visual_body_fat_confidence: low, medium, or high
estimate_type: visual_only
overall_confidence: low, medium, or high
standardized_photo_guidance: array of practical photo consistency tips
safety_flags: array of safety concerns, normally empty

Rules:
- Body-fat estimates must be rough visual-only ranges, not measurements.
- Confidence for visual body-fat should normally be low.
- Do not make exact body-fat claims or medical/skin/disease/hormone claims.
- Be direct, not abusive or humiliating.
"""
VALID_PROGRESS_ANGLES = {"front", "side", "back", "unknown"}
UNSAFE_PROGRESS_TERMS = {
    "gynecomastia",
    "insulin resistance",
    "hormonal problem",
    "hormonal problems",
    "hormone problem",
    "skin condition",
    "skin disease",
    "disease",
    "diagnosis",
    "diagnosed",
    "cancer",
    "mole",
    "melanoma",
    "disgusting",
    "gross",
    "pathetic",
    "lazy slob",
    "starve",
    "starvation",
    "crash diet",
    "purge",
    "purging",
    "dehydrate",
    "dehydration",
    "punish yourself",
    "punishment workout",
}


class StructuredLogValidationError(ValueError):
    """Raised when model-shaped structured log output is unsafe to use."""


class FoodPhotoAnalysisError(ValueError):
    """Raised when food-photo analysis output is unavailable or unsafe to use."""


class ProgressPhotoAnalysisError(ValueError):
    """Raised when progress-photo analysis output is unavailable or unsafe to use."""


class OpenAIFoodPhotoClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def analyze_food_photo(self, image_path: str, caption: str | None = None) -> str:
        if not self.api_key:
            raise FoodPhotoAnalysisError(
                "OPENAI_API_KEY is not configured for food-photo analysis."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency exists in Docker.
            raise FoodPhotoAnalysisError("OpenAI SDK is not installed.") from exc

        image_data = base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")
        caption_text = f"\nCaption: {caption}" if caption else ""
        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{DEFAULT_FOOD_PHOTO_PROMPT}{caption_text}",
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_data}",
                        },
                    ],
                }
            ],
        )
        return str(response.output_text)


class OpenAIProgressPhotoClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def analyze_progress_photo(
        self,
        image_path: str,
        caption: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        if not self.api_key:
            raise ProgressPhotoAnalysisError(
                "OPENAI_API_KEY is not configured for progress-photo analysis."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency exists in Docker.
            raise ProgressPhotoAnalysisError("OpenAI SDK is not installed.") from exc

        image_data = base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")
        caption_text = f"\nCaption: {caption}" if caption else ""
        context_text = f"\nContext: {json.dumps(context or {}, sort_keys=True)}"
        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"{DEFAULT_PROGRESS_PHOTO_PROMPT}"
                                f"{caption_text}{context_text}"
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_data}",
                        },
                    ],
                }
            ],
        )
        return str(response.output_text)


@dataclass(frozen=True)
class StructuredLogExtraction:
    intent: str
    confidence: str
    data: dict[str, Any]
    needs_clarification: bool
    clarification_question: str | None = None


@dataclass(frozen=True)
class FoodPhotoAnalysis:
    photo_type: str
    ai_description: str
    detected_foods: list[str]
    portion_assumptions: list[str]
    calories_estimate: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    confidence: str
    uncertainty_notes: list[str]
    needs_confirmation: bool
    suggested_user_question: str | None = None


@dataclass(frozen=True)
class ProgressPhotoAnalysis:
    photo_type: str
    angle: str
    ai_description: str
    visible_notes: list[str]
    comparison_conditions: dict[str, Any]
    strict_feedback: str
    visual_body_fat_estimate_range: str | None
    visual_body_fat_confidence: str
    estimate_type: str
    overall_confidence: str
    standardized_photo_guidance: list[str]
    safety_flags: list[str]


def extract_structured_log(
    text: str,
    *,
    context: dict[str, Any] | None = None,
    client: object | None = None,
) -> StructuredLogExtraction:
    """Validate a structured-log response without making real network calls.

    Phase 1 deliberately keeps real OpenAI API access disabled here. Service
    code may inject a client with an extract_structured_log method.
    """

    if client is None:
        return StructuredLogExtraction(
            intent="unclear",
            confidence="low",
            data={},
            needs_clarification=True,
            clarification_question="I am not sure what to log. Use /log_meal, /log_weight, or /log_workout.",
        )

    raw_response = client.extract_structured_log(text, context or {})
    payload = _coerce_payload(raw_response)
    return _validate_structured_log(payload)


def analyze_food_photo(
    image_path: str,
    *,
    caption: str | None = None,
    client: object | None = None,
) -> FoodPhotoAnalysis:
    """Validate a food-photo response without making real network calls.

    Real vision calls stay behind this boundary. Startup without configured
    vision support fails gracefully.
    """

    if client is None:
        raise FoodPhotoAnalysisError(
            "OPENAI_API_KEY is not configured for food-photo analysis."
        )

    try:
        raw_response = client.analyze_food_photo(image_path, caption)
    except FoodPhotoAnalysisError:
        raise
    except Exception as exc:
        raise FoodPhotoAnalysisError("Food photo analysis failed.") from exc

    try:
        payload = _coerce_payload(raw_response)
    except StructuredLogValidationError as exc:
        raise FoodPhotoAnalysisError(str(exc)) from exc
    return _validate_food_photo_analysis(payload)


def analyze_progress_photo(
    image_path: str,
    *,
    caption: str | None = None,
    context: dict[str, Any] | None = None,
    client: object | None = None,
) -> ProgressPhotoAnalysis:
    """Validate a progress-photo response without making real network calls."""

    if client is None:
        raise ProgressPhotoAnalysisError(
            "OPENAI_API_KEY is not configured for progress-photo analysis."
        )

    try:
        raw_response = client.analyze_progress_photo(image_path, caption, context or {})
    except ProgressPhotoAnalysisError:
        raise
    except TypeError:
        try:
            raw_response = client.analyze_progress_photo(
                image_path,
                caption=caption,
                context=context or {},
            )
        except ProgressPhotoAnalysisError:
            raise
        except Exception as exc:
            raise ProgressPhotoAnalysisError("Progress photo analysis failed.") from exc
    except Exception as exc:
        raise ProgressPhotoAnalysisError("Progress photo analysis failed.") from exc

    try:
        payload = _coerce_payload(raw_response)
    except StructuredLogValidationError as exc:
        raise ProgressPhotoAnalysisError(str(exc)) from exc
    return _validate_progress_photo_analysis(payload)


def _coerce_payload(raw_response: object) -> dict[str, Any]:
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(_strip_json_fence(raw_response))
        except json.JSONDecodeError as exc:
            raise StructuredLogValidationError("Structured log output is not valid JSON.") from exc
    else:
        parsed = raw_response

    if not isinstance(parsed, dict):
        raise StructuredLogValidationError("Structured log output must be an object.")
    return parsed


def _strip_json_fence(raw_response: str) -> str:
    text = raw_response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _validate_food_photo_analysis(payload: dict[str, Any]) -> FoodPhotoAnalysis:
    photo_type = _required_payload_text(payload, "photo_type")
    if photo_type != "food":
        raise FoodPhotoAnalysisError("Food photo analysis returned a non-food photo.")

    confidence = _required_payload_text(payload, "confidence")
    if confidence not in VALID_CONFIDENCE:
        raise FoodPhotoAnalysisError("Food photo confidence is invalid.")

    detected_foods = _required_text_list(payload, "detected_foods")
    if not detected_foods:
        raise FoodPhotoAnalysisError("Food photo detected_foods cannot be empty.")

    ai_description = _required_payload_text(payload, "ai_description")
    portion_assumptions = _required_text_list(payload, "portion_assumptions")
    uncertainty_notes = _required_text_list(payload, "uncertainty_notes")

    needs_confirmation = payload.get("needs_confirmation")
    if not isinstance(needs_confirmation, bool):
        raise FoodPhotoAnalysisError("needs_confirmation must be boolean.")
    if confidence == "low":
        needs_confirmation = True

    suggested_user_question = payload.get("suggested_user_question")
    if suggested_user_question is not None and not isinstance(
        suggested_user_question,
        str,
    ):
        raise FoodPhotoAnalysisError("suggested_user_question must be text.")

    return FoodPhotoAnalysis(
        photo_type=photo_type,
        ai_description=ai_description,
        detected_foods=detected_foods,
        portion_assumptions=portion_assumptions,
        calories_estimate=_optional_non_negative_number(
            payload,
            "calories_estimate",
            maximum=10000,
        ),
        protein_g=_optional_non_negative_number(payload, "protein_g", maximum=1000),
        carbs_g=_optional_non_negative_number(payload, "carbs_g", maximum=1000),
        fat_g=_optional_non_negative_number(payload, "fat_g", maximum=1000),
        fiber_g=_optional_non_negative_number(payload, "fiber_g", maximum=1000),
        confidence=confidence,
        uncertainty_notes=uncertainty_notes,
        needs_confirmation=needs_confirmation,
        suggested_user_question=suggested_user_question,
    )


def _validate_progress_photo_analysis(payload: dict[str, Any]) -> ProgressPhotoAnalysis:
    photo_type = _required_progress_text(payload, "photo_type")
    if photo_type != "progress":
        raise ProgressPhotoAnalysisError(
            "Progress photo analysis returned a non-progress photo."
        )

    angle = _required_progress_text(payload, "angle")
    if angle not in VALID_PROGRESS_ANGLES:
        raise ProgressPhotoAnalysisError("Progress photo angle is invalid.")

    ai_description = _required_progress_text(payload, "ai_description")
    visible_notes = _required_progress_text_list(payload, "visible_notes")
    comparison_conditions = payload.get("comparison_conditions")
    if not isinstance(comparison_conditions, dict):
        raise ProgressPhotoAnalysisError("comparison_conditions must be an object.")

    strict_feedback = _required_progress_text(payload, "strict_feedback")
    body_fat_range = _optional_progress_text(
        payload,
        "visual_body_fat_estimate_range",
    )
    body_fat_confidence = _required_progress_text(
        payload,
        "visual_body_fat_confidence",
    )
    if body_fat_confidence not in VALID_CONFIDENCE or body_fat_confidence == "high":
        raise ProgressPhotoAnalysisError("Visual body-fat confidence is invalid.")

    estimate_type = _required_progress_text(payload, "estimate_type")
    if estimate_type != "visual_only":
        raise ProgressPhotoAnalysisError("Progress photo estimate_type must be visual_only.")

    overall_confidence = _required_progress_text(payload, "overall_confidence")
    if overall_confidence not in VALID_CONFIDENCE:
        raise ProgressPhotoAnalysisError("Progress photo overall confidence is invalid.")

    guidance = _required_progress_text_list(payload, "standardized_photo_guidance")
    safety_flags = _required_progress_text_list(payload, "safety_flags")
    if body_fat_range is not None:
        _validate_visual_body_fat_range(body_fat_range)

    _validate_progress_safe_texts(
        [
            ai_description,
            strict_feedback,
            body_fat_range,
            *visible_notes,
            *guidance,
            *safety_flags,
        ]
    )

    return ProgressPhotoAnalysis(
        photo_type=photo_type,
        angle=angle,
        ai_description=ai_description,
        visible_notes=visible_notes,
        comparison_conditions=comparison_conditions,
        strict_feedback=strict_feedback,
        visual_body_fat_estimate_range=body_fat_range,
        visual_body_fat_confidence=body_fat_confidence,
        estimate_type=estimate_type,
        overall_confidence=overall_confidence,
        standardized_photo_guidance=guidance,
        safety_flags=safety_flags,
    )


def _validate_structured_log(payload: dict[str, Any]) -> StructuredLogExtraction:
    intent = payload.get("intent")
    confidence = payload.get("confidence")
    data = payload.get("data")

    if intent not in VALID_INTENTS:
        raise StructuredLogValidationError("Structured log intent is invalid.")
    if confidence not in VALID_CONFIDENCE:
        raise StructuredLogValidationError("Structured log confidence is invalid.")
    if not isinstance(data, dict):
        raise StructuredLogValidationError("Structured log data must be an object.")

    _validate_numeric_fields(data)
    _validate_enum_like_fields(data)

    raw_needs_clarification = payload.get("needs_clarification", False)
    if not isinstance(raw_needs_clarification, bool):
        raise StructuredLogValidationError("needs_clarification must be boolean.")
    needs_clarification = raw_needs_clarification or confidence == "low"

    clarification_question = payload.get("clarification_question")
    if clarification_question is not None and not isinstance(clarification_question, str):
        raise StructuredLogValidationError("clarification_question must be text.")

    return StructuredLogExtraction(
        intent=intent,
        confidence=confidence,
        data=data,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
    )


def _required_payload_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FoodPhotoAnalysisError(f"{key} is required.")
    return value.strip()


def _required_progress_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProgressPhotoAnalysisError(f"{key} is required.")
    return value.strip()


def _optional_progress_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProgressPhotoAnalysisError(f"{key} must be text or null.")
    return value.strip()


def _required_progress_text_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ProgressPhotoAnalysisError(f"{key} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ProgressPhotoAnalysisError(f"{key} must contain only text.")
        text = item.strip()
        if text:
            items.append(text)
    return items


def _required_text_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise FoodPhotoAnalysisError(f"{key} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise FoodPhotoAnalysisError(f"{key} must contain only text.")
        text = item.strip()
        if text:
            items.append(text)
    return items


def _validate_progress_safe_texts(texts: list[str | None]) -> None:
    for text in texts:
        if text is None:
            continue
        lowered = text.lower()
        for term in UNSAFE_PROGRESS_TERMS:
            if term in lowered:
                raise ProgressPhotoAnalysisError("Progress photo wording is unsafe.")
        if re.search(r"\byou\s+are\s+\d+(?:\.\d+)?\s*%?\s*body\s*fat\b", lowered):
            raise ProgressPhotoAnalysisError("Progress photo body-fat wording is exact.")
        if re.search(r"\b(your\s+body\s*fat|body\s*fat)\s+is\s+\d+", lowered):
            raise ProgressPhotoAnalysisError("Progress photo body-fat wording is exact.")


def _validate_visual_body_fat_range(text: str) -> None:
    lowered = text.lower()
    if "rough" not in lowered and "visual" not in lowered and "estimate" not in lowered:
        raise ProgressPhotoAnalysisError(
            "Visual body-fat estimate must be phrased as rough visual-only metadata."
        )

    match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*[-–]\s*(\d{1,2}(?:\.\d+)?)\s*%", text)
    if match is None:
        raise ProgressPhotoAnalysisError("Visual body-fat estimate must be a rough range.")

    low = float(match.group(1))
    high = float(match.group(2))
    if low < 3 or high > 70 or low >= high or high - low > 15:
        raise ProgressPhotoAnalysisError("Visual body-fat estimate range is invalid.")

    without_range = text[: match.start()] + text[match.end() :]
    if re.search(r"\b\d{1,2}(?:\.\d+)?\s*%\b", without_range):
        raise ProgressPhotoAnalysisError("Visual body-fat estimate must not be exact.")


def _optional_non_negative_number(
    payload: dict[str, Any],
    key: str,
    *,
    maximum: float,
) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise FoodPhotoAnalysisError(f"{key} must be numeric.")
    if value < 0 or value > maximum:
        raise FoodPhotoAnalysisError(f"{key} is outside the supported range.")
    return float(value)


def _validate_numeric_fields(data: dict[str, Any]) -> None:
    for field_name in NON_NEGATIVE_FIELDS:
        if field_name in data and data[field_name] is not None:
            _require_number_between(
                field_name,
                data[field_name],
                minimum=0,
                maximum=10000 if field_name == "calories_estimate" else 1000,
            )
    if "duration_minutes" in data and data["duration_minutes"] is not None:
        _require_number_between(
            "duration_minutes",
            data["duration_minutes"],
            minimum=1,
            maximum=600,
        )
    if "value" in data and data["value"] is not None:
        _require_number_between("value", data["value"], minimum=0.01, maximum=350)


def _validate_enum_like_fields(data: dict[str, Any]) -> None:
    if "unit" in data and data["unit"] is not None:
        unit = data["unit"]
        if not isinstance(unit, str) or unit.lower() not in VALID_UNITS:
            raise StructuredLogValidationError("unit is invalid.")
    if "measurement_type" in data and data["measurement_type"] is not None:
        measurement_type = data["measurement_type"]
        if (
            not isinstance(measurement_type, str)
            or measurement_type.lower() not in VALID_MEASUREMENT_TYPES
        ):
            raise StructuredLogValidationError("measurement_type is invalid.")


def _require_number_between(
    field_name: str,
    value: object,
    *,
    minimum: float,
    maximum: float,
) -> None:
    if not isinstance(value, int | float):
        raise StructuredLogValidationError(f"{field_name} must be numeric.")
    if value < minimum or value > maximum:
        raise StructuredLogValidationError(f"{field_name} is outside the supported range.")
