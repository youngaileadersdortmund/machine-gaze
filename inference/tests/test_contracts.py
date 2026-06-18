import pytest
from pydantic import ValidationError

from inference.contracts import BigFiveReport, normalize_report


def trait(key: str, score: int = 50) -> dict:
    return {
        "key": key,
        "name": key,
        "scorePercent": score,
        "lowLabel": "low",
        "highLabel": "high",
        "summary": f"{key} summary",
    }


def report_payload(traits: list[dict] | None = None) -> dict:
    return {
        "traits": traits
        or [
            trait("neuroticism", 20),
            trait("agreeableness", 70),
            trait("extraversion", 60),
            trait("conscientiousness", 55),
            trait("openness", 80),
        ],
        "machineGuess": {
            "probablyStudies": "Design, media, or something with too many deadlines.",
            "campusRole": "The person who quietly becomes project lead.",
            "futureForecast": "Will accidentally become responsible for the group chat.",
            "classicStruggle": "Says yes because it looks quick.",
        },
        "model": {"name": "fake", "version": "test"},
    }


def test_big_five_report_orders_traits():
    report = BigFiveReport.model_validate(report_payload())

    assert [item.key for item in report.traits] == [
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    ]


def test_big_five_report_rejects_invalid_trait_set():
    with pytest.raises(ValidationError):
        BigFiveReport.model_validate(report_payload(traits=[trait("openness")] * 5))


def test_normalize_report_forces_canonical_labels_and_model():
    report = normalize_report(
        BigFiveReport.model_validate(report_payload()),
        model_name="gemini-2.5-flash",
        model_version="vertex-ai:us-central1",
    )

    assert report.model.name == "gemini-2.5-flash"
    assert report.traits[0].name == "Openness"
    assert report.traits[2].lowLabel == "Introverted"
    assert report.traits[2].highLabel == "Extraverted"
    assert report.machineGuess.campusRole == "The person who quietly becomes project lead."


def test_big_five_report_requires_machine_guess():
    payload = report_payload()
    payload.pop("machineGuess")

    with pytest.raises(ValidationError):
        BigFiveReport.model_validate(payload)
