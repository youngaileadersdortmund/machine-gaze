from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from .contracts import BigFiveReport, ModelMetadata, normalize_report
from .prompts import MASTER_PROMPT, USER_PROMPT
from .settings import InferenceSettings


class Analyzer(Protocol):
    model_name: str
    model_version: str

    def analyze(self, image_path: str | Path) -> BigFiveReport:
        ...


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


def parse_report_payload(payload: object) -> BigFiveReport:
    if isinstance(payload, BigFiveReport):
        return payload
    return BigFiveReport.model_validate(payload)


def parse_report_text(text: str) -> BigFiveReport:
    return parse_report_payload(json.loads(extract_json_object(text)))


class GeminiBigFiveAnalyzer:
    model_version = "vertex-ai"

    def __init__(self, settings: InferenceSettings):
        if not settings.google_cloud_project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required for Gemini inference. "
                "Set it after running `gcloud auth application-default login`."
            )

        from google import genai
        from google.genai import types

        self.settings = settings
        self.model_name = settings.gemini_model_id
        self.model_version = f"vertex-ai:{settings.google_cloud_location}"
        self.types = types
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    def _image_part(self, image_path: Path):
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        return self.types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)

    def _generate_report_once(self, image_path: Path, *, attempt: int) -> BigFiveReport:
        config = self.types.GenerateContentConfig(
            system_instruction=MASTER_PROMPT,
            temperature=self.settings.temperature,
            max_output_tokens=self.settings.max_output_tokens,
            response_mime_type="application/json",
            response_schema=BigFiveReport,
        )
        response = self.client.models.generate_content(
            model=self.settings.gemini_model_id,
            contents=[self._image_part(image_path), USER_PROMPT],
            config=config,
        )

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            print(f"[gemini] parsed response attempt {attempt}:", flush=True)
            if hasattr(parsed, "model_dump_json"):
                print(parsed.model_dump_json(indent=2), flush=True)
            else:
                print(json.dumps(parsed, indent=2, default=str), flush=True)
            return parse_report_payload(parsed)

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini did not return a Big Five report.")
        print(f"[gemini] raw response attempt {attempt}:", flush=True)
        print(text, flush=True)
        return parse_report_text(text)

    def _generate_report(self, image_path: Path) -> BigFiveReport:
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                return self._generate_report_once(image_path, attempt=attempt)
            except (json.JSONDecodeError, ValidationError, ValueError, RuntimeError) as exc:
                last_error = exc
                print(f"[gemini] invalid response attempt {attempt}: {exc}", flush=True)
                if attempt == 1:
                    print("[gemini] retrying once with the same image and schema.", flush=True)

        raise RuntimeError(f"Gemini returned an invalid Big Five report after retry: {last_error}")

    def analyze(self, image_path: str | Path) -> BigFiveReport:
        image_path = Path(image_path)
        try:
            report = self._generate_report(image_path)
        except RuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

        normalized = normalize_report(
            report.model_copy(update={"model": ModelMetadata(name=self.model_name, version=self.model_version)}),
            model_name=self.model_name,
            model_version=self.model_version,
        )
        print("[gemini] normalized report:", flush=True)
        print(normalized.model_dump_json(indent=2), flush=True)
        return normalized


def build_analyzer(settings: InferenceSettings | None = None) -> Analyzer:
    return GeminiBigFiveAnalyzer(settings or InferenceSettings.from_env())
