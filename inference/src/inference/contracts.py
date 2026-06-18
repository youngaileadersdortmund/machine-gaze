from typing import Literal

from pydantic import BaseModel, Field, model_validator

TraitKey = Literal["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

REQUIRED_TRAIT_KEYS: tuple[TraitKey, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

TRAIT_DEFAULTS: dict[TraitKey, dict[str, str]] = {
    "openness": {
        "name": "Openness",
        "lowLabel": "Practical",
        "highLabel": "Curious",
    },
    "conscientiousness": {
        "name": "Conscientiousness",
        "lowLabel": "Spontaneous",
        "highLabel": "Organized",
    },
    "extraversion": {
        "name": "Extraversion",
        "lowLabel": "Introverted",
        "highLabel": "Extraverted",
    },
    "agreeableness": {
        "name": "Agreeableness",
        "lowLabel": "Skeptical",
        "highLabel": "Cooperative",
    },
    "neuroticism": {
        "name": "Neuroticism",
        "lowLabel": "Calm",
        "highLabel": "Reactive",
    },
}


class TraitReport(BaseModel):
    key: TraitKey
    name: str = Field(min_length=1, max_length=40)
    scorePercent: int = Field(ge=0, le=100)
    lowLabel: str = Field(min_length=1, max_length=40)
    highLabel: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=220)


class ModelMetadata(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)


class MachineGuess(BaseModel):
    probablyStudies: str = Field(min_length=1, max_length=160)
    campusRole: str = Field(min_length=1, max_length=160)
    futureForecast: str = Field(min_length=1, max_length=180)
    classicStruggle: str = Field(min_length=1, max_length=180)


class BigFiveReport(BaseModel):
    traits: list[TraitReport]
    machineGuess: MachineGuess
    model: ModelMetadata

    @model_validator(mode="after")
    def validate_trait_set(self) -> "BigFiveReport":
        keys = [trait.key for trait in self.traits]
        if len(keys) != len(REQUIRED_TRAIT_KEYS):
            raise ValueError("Report must include exactly five Big Five traits.")
        if len(set(keys)) != len(keys):
            raise ValueError("Report contains duplicate Big Five traits.")
        missing = set(REQUIRED_TRAIT_KEYS) - set(keys)
        extra = set(keys) - set(REQUIRED_TRAIT_KEYS)
        if missing or extra:
            raise ValueError("Report must include exactly the Big Five trait keys.")

        trait_by_key = {trait.key: trait for trait in self.traits}
        self.traits = [trait_by_key[key] for key in REQUIRED_TRAIT_KEYS]
        return self


def normalize_report(report: BigFiveReport, *, model_name: str, model_version: str) -> BigFiveReport:
    traits = []
    for trait in report.traits:
        defaults = TRAIT_DEFAULTS[trait.key]
        traits.append(
            trait.model_copy(
                update={
                    "name": defaults["name"],
                    "lowLabel": defaults["lowLabel"],
                    "highLabel": defaults["highLabel"],
                }
            )
        )
    return BigFiveReport(
        traits=traits,
        machineGuess=report.machineGuess,
        model=ModelMetadata(name=model_name, version=model_version),
    )
