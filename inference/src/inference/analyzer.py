from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Protocol

from PIL import Image
from pydantic import ValidationError

from .contracts import InsightGroup, ModelMetadata, PrivacyReport
from .settings import InferenceSettings

SENSITIVE_TERMS = {
    "age",
    "ethnicity",
    "gender",
    "health",
    "income",
    "politic",
    "pregnan",
    "race",
    "religion",
    "sexual",
    "wealth",
}

REPORT_PROMPT = """You are Machine Gaze, a privacy-literacy demo for students.
Analyze the uploaded photo and return ONLY one valid JSON object matching this schema:
{
  "riskScore": 0-100,
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


class Analyzer(Protocol):
    model_name: str
    model_version: str

    def analyze(self, image_path: str | Path) -> PrivacyReport:
        ...


def _contains_sensitive_term(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in SENSITIVE_TERMS)


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
    return safety_postprocess(PrivacyReport.model_validate(payload))


def calibrate_risk_score(report: PrivacyReport) -> int:
    observed_text = " ".join(item.lower() for group in report.observed for item in group.items)
    score = report.riskScore
    weighted_terms = {
        "face": 10,
        "person": 6,
        "text": 10,
        "ocr": 10,
        "badge": 12,
        "location": 10,
        "background": 5,
        "reflection": 5,
        "license": 15,
    }
    deterministic_floor = 20 + sum(weight for term, weight in weighted_terms.items() if term in observed_text)
    return _clamp_score(max(score, deterministic_floor))


def safety_postprocess(report: PrivacyReport) -> PrivacyReport:
    removed_items: list[str] = []
    safe_observed: list[InsightGroup] = []

    for group in report.observed:
        safe_items = []
        for item in group.items:
            if _contains_sensitive_term(item):
                removed_items.append(item)
            else:
                safe_items.append(item)
        if safe_items:
            safe_observed.append(group.model_copy(update={"items": safe_items}))

    if not safe_observed:
        safe_observed.append(
            InsightGroup(
                title="Image properties",
                confidence="high",
                items=["photo was received and decoded for visual privacy analysis"],
            )
        )

    speculative = [
        group.model_copy(update={"confidence": "low"})
        for group in report.speculative
    ]
    unsafe_group_index = next(
        (index for index, group in enumerate(speculative) if "unsafe" in group.title.lower()),
        None,
    )
    unsafe_items = ["politics", "religion", "sexual orientation", "health status", "income"]
    if removed_items:
        unsafe_items.extend(f"removed unsupported claim: {item}" for item in removed_items[:3])

    if unsafe_group_index is None:
        speculative.append(
            InsightGroup(title="Unsafe overreach", confidence="low", items=unsafe_items[:8])
        )
    else:
        group = speculative[unsafe_group_index]
        merged = list(dict.fromkeys([*group.items, *unsafe_items]))[:8]
        speculative[unsafe_group_index] = group.model_copy(update={"items": merged})

    safety_notes = list(report.safetyNotes)
    note = "Protected and sensitive traits are unsafe overreach examples, not factual predictions."
    if note not in safety_notes:
        safety_notes.append(note)

    return report.model_copy(
        update={
            "riskScore": calibrate_risk_score(report),
            "observed": safe_observed[:8],
            "speculative": speculative[:8],
            "safetyNotes": safety_notes[:8],
        }
    )


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

        return safety_postprocess(
            PrivacyReport(
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
                    InsightGroup(
                        title="Unsafe overreach",
                        confidence="low",
                        items=[
                            "religion",
                            "politics",
                            "sexual orientation",
                            "health status",
                        ],
                    ),
                ],
                targeting=["visual privacy", "campus event", "AI literacy"],
                safetyNotes=[
                    "Protected and sensitive traits must not be presented as factual predictions.",
                    "Unsafe overreach examples are shown to teach privacy risk, not to profile participants.",
                ],
                model=ModelMetadata(name=self.model_name, version=self.model_version),
            )
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
    if _qwen_runtime_available(active_settings):
        return QwenAnalyzer(active_settings)
    return StubAnalyzer()


def analyze_image(image_path: str | Path) -> PrivacyReport:
    return StubAnalyzer().analyze(image_path)
