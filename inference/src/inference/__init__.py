from .analyzer import QwenAnalyzer, StubAnalyzer, analyze_image, build_analyzer
from .contracts import InsightGroup, ModelMetadata, PrivacyReport


def main() -> None:
    print("Inference package ready. Use inference.worker for backend job processing.")


__all__ = [
    "InsightGroup",
    "ModelMetadata",
    "PrivacyReport",
    "QwenAnalyzer",
    "StubAnalyzer",
    "analyze_image",
    "build_analyzer",
    "main",
]
