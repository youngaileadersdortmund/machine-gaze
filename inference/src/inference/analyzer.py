from __future__ import annotations

import base64
import importlib.util
import json
import mimetypes
from pathlib import Path
from typing import Protocol

import httpx
import google.auth
from google.auth.transport.requests import Request
from PIL import Image
from pydantic import ValidationError

from .contracts import InsightGroup, ModelMetadata, PrivacyReport
from .settings import InferenceSettings

GOOGLE_VISION_FEATURES = [
    {"type": "LABEL_DETECTION", "maxResults": 12},
    {"type": "OBJECT_LOCALIZATION", "maxResults": 12},
    {"type": "TEXT_DETECTION", "maxResults": 8},
    {"type": "FACE_DETECTION", "maxResults": 8},
    {"type": "LANDMARK_DETECTION", "maxResults": 6},
    {"type": "LOGO_DETECTION", "maxResults": 6},
    {"type": "SAFE_SEARCH_DETECTION"},
    {"type": "IMAGE_PROPERTIES", "maxResults": 8},
]

LOW_VALUE_LABEL_TERMS = {
    "body",
    "cheek",
    "chin",
    "ear",
    "eyebrow",
    "face",
    "forehead",
    "hair",
    "head",
    "human",
    "jaw",
    "lip",
    "mouth",
    "nose",
    "person",
    "photograph",
    "skin",
    "standing",
}

CLOTHING_TERMS = {
    "blazer",
    "coat",
    "collar",
    "dress shirt",
    "eyeglasses",
    "eyewear",
    "formal wear",
    "glasses",
    "jacket",
    "necktie",
    "shirt",
    "shoe",
    "suit",
    "tie",
    "watch",
}

SCENE_TERMS = {
    "architecture",
    "building",
    "facade",
    "garden",
    "grass",
    "indoor",
    "office",
    "outdoor",
    "palm",
    "plant",
    "road",
    "room",
    "sidewalk",
    "street",
    "tree",
    "urban",
    "wall",
    "window",
}

SAFE_SEARCH_SIGNALS = {"LIKELY", "VERY_LIKELY", "POSSIBLE"}

REPORT_PROMPT = """You are Machine Gaze, a privacy-literacy demo for students.
Analyze the uploaded photo and return ONLY one valid JSON object matching this schema:
{
  "observed": [{"title": string, "confidence": "high"|"medium"|"low", "items": [string]}],
  "speculative": [{"title": string, "confidence": "low", "items": [string]}],
  "targeting": [string],
  "safetyNotes": [string],
  "model": {"name": string, "version": string}
}

Rules:
- observed must contain only visible, grounded signals: scene, objects, readable text/OCR, image quality, clothing/accessories, and background/location clues.
- speculative must contain only weak, low-confidence profile-style guesses and an "Unsafe overreach" group.
- Never state protected or sensitive traits as facts, including politics, religion, health, sexuality, ethnicity, income, or identity.
- targeting is an ad-targeting simulation, not a real profile.
- Keep each group concise. No markdown. No prose outside JSON.
"""

GEMINI_REPORT_PROMPT = """You are Machine Gaze, a theatrical persona-analysis engine for an interactive art demo.
Analyze the uploaded photo and return ONLY one valid JSON object matching this schema:
{
  "observed": [{"title": string, "confidence": "medium", "items": [string]}],
  "speculative": [{"title": string, "confidence": "low", "items": [string]}],
  "targeting": [string],
  "safetyNotes": [string],
  "model": {"name": string, "version": string}
}

The confidence field is a legacy compatibility field. Use "medium" confidence for observed
groups and "low" confidence for speculative groups. Do not write about scores, certainty,
confidence, probability, safety, or model limitations in the report.

Write a vivid personality dossier, not object detection and not a safety lecture.
The report should feel like a sharp magazine profile or cold-read: stylish, specific,
slightly unsettling, and based on the image's pose, styling, expression, setting, and composition.

Use observed for persona-read sections such as:
- First impression
- Social mask
- Style and status signals
- Energy in the frame
- Tensions and contradictions

Use speculative for deeper personality-read sections such as:
- Likely operating mode
- Social strategy
- Under pressure
- Blind spots
- What this image is trying to make you believe

Rules:
- Do not list obvious objects unless they support a personality interpretation.
- Prefer phrases like "comes across as", "signals", "suggests", "reads as", "projects", and "the image performs".
- Avoid bland lines like "wearing glasses", "dark hair", "outdoor setting", or "white shirt" unless tied to a persona claim.
- Do not create an Unsafe overreach section. Leave safetyNotes empty unless there is a real model limitation.
- Do not infer or state protected/sensitive traits: race, ethnicity, nationality, politics, religion, health, sexuality, gender identity, pregnancy, income, or wealth.
- targeting should be influence hooks or ad/algorithmic categories, e.g. executive coaching, luxury grooming, premium eyewear, networking events, productivity apps, reputation management, portrait photography.
- Keep each group concise: 3-5 punchy items. No markdown. No prose outside JSON.
"""


class Analyzer(Protocol):
    model_name: str
    model_version: str

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        ...


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()

    start = stripped.find("{")
    if start < 0:
        raise ValueError("Model output did not contain a JSON object.")

    depth = 0
    in_string = False
    escaped = False
    for index, character in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]

    raise ValueError("Model output contained incomplete JSON.")


def _string_list(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def normalize_report_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Model output JSON was not an object.")

    normalized: dict[str, object] = dict(payload)
    normalized["riskScore"] = _clamp_score(int(normalized.get("riskScore") or 50))

    observed = []
    for group in normalized.get("observed") or []:
        if not isinstance(group, dict):
            continue
        items = _string_list(group.get("items"), limit=8)
        if not items:
            continue
        confidence = group.get("confidence")
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        observed.append(
            {
                "title": str(group.get("title") or "Visual observations")[:80],
                "confidence": confidence,
                "items": items,
            }
        )

    if not observed:
        observed.append(
            {
                "title": "Visual observations",
                "confidence": "medium",
                "items": ["the model returned a sparse visual report for this image"],
            }
        )
    normalized["observed"] = observed[:8]

    speculative = []
    for group in normalized.get("speculative") or []:
        if not isinstance(group, dict):
            continue
        items = _string_list(group.get("items"), limit=8)
        if not items:
            continue
        speculative.append(
            {
                "title": str(group.get("title") or "Plausible but uncertain assumptions")[:80],
                "confidence": "low",
                "items": items,
            }
        )
    normalized["speculative"] = speculative[:8]
    normalized["targeting"] = _string_list(normalized.get("targeting"), limit=12)
    normalized["safetyNotes"] = _string_list(normalized.get("safetyNotes"), limit=8)

    model = normalized.get("model")
    if not isinstance(model, dict):
        model = {}
    normalized["model"] = {
        "name": str(model.get("name") or "unknown")[:120],
        "version": str(model.get("version") or "unknown")[:80],
    }
    return normalized


def parse_report_text(text: str) -> PrivacyReport:
    raw_json = extract_json_object(text)
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
        except ImportError:
            raise
        payload = json.loads(repair_json(raw_json))
    payload = normalize_report_payload(payload)
    return PrivacyReport.model_validate(payload)


def parse_creative_report_text(text: str) -> PrivacyReport:
    raw_json = extract_json_object(text)
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
        except ImportError:
            raise
        payload = json.loads(repair_json(raw_json))
    payload = normalize_report_payload(payload)
    payload["riskScore"] = 0
    return PrivacyReport.model_validate(payload)


class StubAnalyzer:
    model_name = "machine-gaze-stub"
    model_version = "0.1.0"

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        with Image.open(image_path) as image:
            width, height = image.size
            mode = image.mode

        risk_score = 45
        if width >= 1000 or height >= 1000:
            risk_score += 10
        if mode in {"RGB", "RGBA"}:
            risk_score += 5

        return PrivacyReport(
            riskScore=min(risk_score, 100),
            observed=[
                InsightGroup(
                    title="Image properties",
                    confidence="high",
                    items=[
                        f"image resolution is {width} by {height} pixels",
                        f"color mode is {mode}",
                        "metadata has been stripped before analysis",
                    ],
                ),
                InsightGroup(
                    title="Privacy exposure",
                    confidence="medium",
                    items=[
                        "a single photo can expose scene context",
                        "visible text, faces, clothing, and background details may reveal affiliation",
                    ],
                ),
            ],
            speculative=[
                InsightGroup(
                    title="Weak profile guesses",
                    confidence="low",
                    items=[
                        "profile-style guesses are unreliable from one image",
                        "the demo labels such guesses as speculation, not truth",
                    ],
                ),
            ],
            targeting=["visual privacy", "campus event", "AI literacy"],
            safetyNotes=[],
            model=ModelMetadata(name=self.model_name, version=self.model_version),
        )


def _score_label(entity: dict) -> str:
    description = entity.get("description") or entity.get("name") or "unknown"
    score = entity.get("score")
    if isinstance(score, int | float):
        return f"{description} ({score:.0%} confidence)"
    return description


def _annotation_name(annotation: str) -> str:
    return annotation.split(" (", 1)[0].strip()


def _annotation_key(annotation: str) -> str:
    return _annotation_name(annotation).lower()


def _matches_terms(annotation: str, terms: set[str]) -> bool:
    key = _annotation_key(annotation)
    return any(term in key for term in terms)


def _meaningful_annotations(annotations: list[str], *, exclude: set[str] | None = None) -> list[str]:
    excluded_terms = exclude or set()
    return [
        annotation
        for annotation in annotations
        if not _matches_terms(annotation, LOW_VALUE_LABEL_TERMS | excluded_terms)
    ]


def _likelihood(value: str | None) -> str:
    return (value or "UNKNOWN").replace("_", " ").lower()


def _top_items(items: list[str], fallback: str, limit: int = 8) -> list[str]:
    unique = list(dict.fromkeys(item for item in items if item))
    return unique[:limit] or [fallback]


def _targeting_tag(annotation: str) -> str | None:
    tag = _annotation_key(annotation)
    if not tag or tag == "unknown":
        return None
    return tag


def _ad_categories(annotations: list[str], detected_text: list[str], logos: list[str]) -> list[str]:
    categories: list[str] = []
    annotation_text = " ".join(_annotation_key(annotation) for annotation in annotations)

    if any(term in annotation_text for term in {"suit", "tie", "coat", "blazer", "formal wear", "collar"}):
        categories.extend(["formalwear", "business attire", "professional headshots"])
    if any(term in annotation_text for term in {"glasses", "eyewear", "eyeglasses", "vision care"}):
        categories.extend(["eyewear", "vision care"])
    if any(term in annotation_text for term in {"plant", "tree", "grass", "outdoor", "garden"}):
        categories.extend(["outdoor portraits", "landscaping"])
    if detected_text:
        categories.extend(["OCR-based retargeting", "brand or workplace lookup"])
    if logos:
        categories.append("brand affinity")

    categories.extend(
        tag
        for tag in (_targeting_tag(annotation) for annotation in annotations)
        if tag and not _matches_terms(tag, LOW_VALUE_LABEL_TERMS)
    )
    return _top_items(categories, "visual privacy education", limit=12)


class GoogleVisionAnalyzer:
    model_name = "google-cloud-vision"
    model_version = "v1-images-annotate"
    scopes = ("https://www.googleapis.com/auth/cloud-platform",)

    def __init__(self, settings: InferenceSettings):
        self.credentials, self.project_id = google.auth.default(scopes=self.scopes)
        if settings.google_cloud_quota_project and hasattr(self.credentials, "with_quota_project"):
            self.credentials = self.credentials.with_quota_project(settings.google_cloud_quota_project)
        self.auth_request = Request()

    def _headers(self) -> dict[str, str]:
        if not self.credentials.valid:
            self.credentials.refresh(self.auth_request)

        headers = {"Authorization": f"Bearer {self.credentials.token}"}
        quota_project_id = getattr(self.credentials, "quota_project_id", None)
        if quota_project_id:
            headers["x-goog-user-project"] = quota_project_id
        return headers

    def _annotate(self, image_path: Path) -> dict:
        content = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "requests": [
                {
                    "image": {"content": content},
                    "features": GOOGLE_VISION_FEATURES,
                }
            ]
        }
        response = httpx.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers=self._headers(),
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()["responses"][0]
        if "error" in result:
            message = result["error"].get("message", "Google Vision returned an error.")
            raise RuntimeError(message)
        return result

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        image_path = Path(image_path)
        result = self._annotate(image_path)

        labels = [_score_label(entity) for entity in result.get("labelAnnotations", [])]
        objects = [_score_label(entity) for entity in result.get("localizedObjectAnnotations", [])]
        logos = [_score_label(entity) for entity in result.get("logoAnnotations", [])]
        landmarks = [_score_label(entity) for entity in result.get("landmarkAnnotations", [])]
        all_annotations = [*objects, *labels]

        text_annotations = result.get("textAnnotations", [])
        detected_text = []
        if text_annotations:
            full_text = text_annotations[0].get("description", "").strip().replace("\n", " / ")
            if full_text:
                detected_text.append(f"readable text detected: {full_text[:180]}")
            detected_text.extend(_score_label(entity) for entity in text_annotations[1:6])

        face_annotations = result.get("faceAnnotations", [])
        people_items = []
        if face_annotations:
            people_items.append(f"{len(face_annotations)} visible face-like region(s) detected")
            people_items.append("face detection enables biometric-style matching and photo clustering")
            first_face = face_annotations[0]
            emotion_items = [
                f"{name} {_likelihood(first_face.get(field))}"
                for name, field in [
                    ("joy", "joyLikelihood"),
                    ("sorrow", "sorrowLikelihood"),
                    ("anger", "angerLikelihood"),
                    ("surprise", "surpriseLikelihood"),
                ]
            ]
            people_items.append(f"expression signals returned by Vision: {', '.join(emotion_items)}")
        else:
            people_items.append("no face-like regions detected by Google Vision")

        safe_search = result.get("safeSearchAnnotation", {})
        safety_items = [
            f"{key.replace('_', ' ')} likelihood is {_likelihood(value)}"
            for key, value in safe_search.items()
            if key in {"adult", "violence", "racy", "medical", "spoof"} and value in SAFE_SEARCH_SIGNALS
        ]

        clothing_items = _meaningful_annotations(
            [annotation for annotation in all_annotations if _matches_terms(annotation, CLOTHING_TERMS)]
        )
        scene_items = _meaningful_annotations(
            [annotation for annotation in all_annotations if _matches_terms(annotation, SCENE_TERMS)]
        )
        object_items = _meaningful_annotations(
            [
                annotation
                for annotation in all_annotations
                if not _matches_terms(annotation, CLOTHING_TERMS | SCENE_TERMS)
            ]
        )

        observed = [
            InsightGroup(
                title="People",
                confidence="medium" if face_annotations else "low",
                items=_top_items(people_items, "no people signals returned by Google Vision"),
            )
        ]
        if clothing_items:
            observed.append(
                InsightGroup(
                    title="Clothing and accessories",
                    confidence="high",
                    items=_top_items(clothing_items, "no clothing or accessory signals returned"),
                )
            )
        if scene_items:
            observed.append(
                InsightGroup(
                    title="Scene and background",
                    confidence="medium",
                    items=_top_items(scene_items, "no scene or background signals returned"),
                )
            )
        if object_items:
            observed.append(
                InsightGroup(
                    title="Other visual signals",
                    confidence="medium",
                    items=_top_items(object_items, "no additional visual signals returned"),
                )
            )
        if detected_text:
            observed.append(InsightGroup(title="Text", confidence="high", items=_top_items(detected_text, "")))
        if logos or landmarks:
            observed.append(
                InsightGroup(
                    title="Places and brands",
                    confidence="medium",
                    items=_top_items([*logos, *landmarks], "no places or brands returned"),
                )
            )
        if safety_items:
            observed.append(InsightGroup(title="Flagged content signals", confidence="medium", items=safety_items))

        speculative = [
            InsightGroup(
                title="Unsafe overreach",
                confidence="low",
                items=[
                    "race is not inferred from the image",
                    "religion is not inferred from the image",
                    "sexual orientation is not inferred from the image",
                    "political affiliation is not inferred from the image",
                    "income range is not inferred from the image",
                ],
            ),
            InsightGroup(
                title="Weak profile guesses",
                confidence="low",
                items=[
                    "formal clothing can be used to guess professional context, but the guess may be wrong",
                    "eyewear and clothing can feed ad categories without proving identity or intent",
                    "ad categories below are simulated from visible cues, not a real profile",
                ],
            ),
        ]

        targeting = _ad_categories([*all_annotations, *logos], detected_text, logos)

        risk_score = 35
        if face_annotations:
            risk_score += 15
        if detected_text:
            risk_score += 15
        if logos or landmarks:
            risk_score += 10
        if clothing_items or scene_items or object_items:
            risk_score += 8

        return PrivacyReport(
            riskScore=_clamp_score(risk_score),
            observed=observed[:8],
            speculative=speculative,
            targeting=targeting,
            safetyNotes=[],
            model=ModelMetadata(name=self.model_name, version=self.model_version),
        )


class GeminiAnalyzer:
    model_version = "vertex-ai"

    def __init__(self, settings: InferenceSettings):
        settings.apply_environment()
        self.settings = settings
        self.model_name = settings.gemini_model_id
        self.model_version = f"vertex-ai:{settings.google_cloud_location}"

        from google import genai
        from google.genai import types

        project = settings.google_cloud_project
        if not project:
            _, project = google.auth.default(scopes=GoogleVisionAnalyzer.scopes)
        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required for the Gemini analyzer. "
                "Set it with `gcloud config set project YOUR_PROJECT_ID` and export GOOGLE_CLOUD_PROJECT."
            )

        self.types = types
        self.client = genai.Client(
            enterprise=settings.google_genai_use_enterprise,
            vertexai=True,
            project=project,
            location=settings.google_cloud_location,
        )

    def _image_part(self, image_path: Path):
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        return self.types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)

    def _generate_text(self, contents: list[object]) -> str:
        config = self.types.GenerateContentConfig(
            temperature=0.45,
            maxOutputTokens=self.settings.max_new_tokens,
            responseMimeType="application/json",
            responseSchema=PrivacyReport,
        )
        response = self.client.models.generate_content(
            model=self.settings.gemini_model_id,
            contents=contents,
            config=config,
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini did not return text.")
        return text

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        image_path = Path(image_path)
        first_output = self._generate_text([self._image_part(image_path), GEMINI_REPORT_PROMPT])
        try:
            report = parse_creative_report_text(first_output)
        except (ValueError, json.JSONDecodeError, ValidationError):
            repair_prompt = (
                "Repair this output into one valid JSON object matching the Machine Gaze "
                "PrivacyReport schema. Return JSON only.\n\n"
                f"Output:\n{first_output}"
            )
            try:
                report = parse_creative_report_text(self._generate_text([repair_prompt]))
            except (ValueError, json.JSONDecodeError, ValidationError) as repair_error:
                raise RuntimeError(
                    f"Gemini did not produce a valid privacy report: {repair_error}"
                ) from repair_error

        return report.model_copy(
            update={"model": ModelMetadata(name=self.model_name, version=self.model_version)}
        )


class QwenAnalyzer:
    def __init__(self, settings: InferenceSettings):
        settings.apply_environment()
        self.settings = settings
        self.model_name = settings.model_id
        self.model_version = "transformers"

        import torch
        from transformers import AutoProcessor, Qwen3VLMoeForConditionalGeneration

        self.torch = torch
        kwargs: dict[str, object] = {
            "dtype": "auto",
            "device_map": settings.device_mode,
        }
        if settings.attn_implementation:
            kwargs["attn_implementation"] = settings.attn_implementation

        self.processor = AutoProcessor.from_pretrained(settings.model_id)
        self.model = Qwen3VLMoeForConditionalGeneration.from_pretrained(settings.model_id, **kwargs)

    def _model_device(self):
        if hasattr(self.model, "device"):
            return self.model.device
        return next(self.model.parameters()).device

    def _generate_text(self, messages: list[dict]) -> str:
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self._model_device())
        with self.torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.settings.max_new_tokens,
                do_sample=False,
            )
        generated = outputs[:, inputs["input_ids"].shape[-1] :]
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0]

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        image_path = Path(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": REPORT_PROMPT},
                ],
            }
        ]
        first_output = self._generate_text(messages)
        try:
            report = parse_report_text(first_output)
        except (ValueError, json.JSONDecodeError, ValidationError) as first_error:
            repair_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Repair this output into one valid JSON object matching the Machine Gaze "
                                f"PrivacyReport schema. Return JSON only.\n\nOutput:\n{first_output}"
                            ),
                        }
                    ],
                }
            ]
            try:
                report = parse_report_text(self._generate_text(repair_messages))
            except (ValueError, json.JSONDecodeError, ValidationError) as repair_error:
                raise RuntimeError("Model did not produce a valid privacy report.") from repair_error
            if not report.safetyNotes:
                raise RuntimeError("Model repair produced a report without safety notes.") from first_error

        return report.model_copy(
            update={"model": ModelMetadata(name=self.model_name, version=self.model_version)}
        )


def _qwen_runtime_available(settings: InferenceSettings) -> bool:
    if not importlib.util.find_spec("torch") or not importlib.util.find_spec("transformers"):
        return False
    try:
        import torch
    except ImportError:
        return False
    if settings.device_mode == "cpu":
        return True
    return bool(torch.cuda.is_available())


def build_analyzer(settings: InferenceSettings | None = None) -> Analyzer:
    active_settings = settings or InferenceSettings.from_env()
    mode = active_settings.analyzer.lower()
    if mode == "stub":
        return StubAnalyzer()
    if mode == "qwen":
        return QwenAnalyzer(active_settings)
    if mode == "gemini":
        return GeminiAnalyzer(active_settings)
    if mode in {"google", "google-vision", "vision"}:
        return GoogleVisionAnalyzer(active_settings)
    if _qwen_runtime_available(active_settings):
        return QwenAnalyzer(active_settings)
    return StubAnalyzer()


def analyze_image(image_path: str | Path) -> PrivacyReport:
    return StubAnalyzer().analyze(image_path)
