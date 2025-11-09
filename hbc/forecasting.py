from __future__ import annotations

import random
from typing import List, Sequence, Tuple

__all__ = ["generate_synthetic_forecast"]


def generate_synthetic_forecast(
    region: str, horizon: int, modalities: Sequence[str]
) -> Tuple[float, float, List[str]]:
    """Return a deterministic synthetic forecast for the requested inputs.

    Args:
        region: Region identifier (free-form string).
        horizon: Forecast horizon in days. Expected to be validated upstream.
        modalities: Modalities contributing to the forecast (order-agnostic).

    Returns:
        Tuple of (forecast value, confidence value, explanation list).
    """

    normalized_modalities = list(modalities)
    seed = f"{region.lower()}:{horizon}:{','.join(sorted(normalized_modalities))}"
    rng = random.Random(seed)

    base = rng.uniform(0.45, 0.85)
    modality_factor = 1.0 + 0.05 * len(normalized_modalities)
    forecast_value = round(base * modality_factor, 3)
    confidence = round(min(0.99, 0.55 + rng.random() * 0.35), 3)

    explanations: List[str] = []
    if normalized_modalities:
        for modality in normalized_modalities:
            weight = round(0.3 + rng.random() * 0.5, 3)
            explanations.append(f"{modality} contribution: {weight}")
    else:
        explanations.append("baseline synthetic trend applied")

    return forecast_value, confidence, explanations
