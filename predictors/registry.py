# SPDX-License-Identifier: MIT-0
import importlib.metadata
from typing import Any, Dict, Type

"""
Plugin registry for behavioral predictors.
Allows dynamic discovery and loading of predictor plugins via entry points.
"""

PREDICTOR_ENTRY_POINT = "human_behaviour_predictor"


class PredictorRegistry:
    def __init__(self) -> None:
        self._predictors: Dict[str, Type[Any]] = {}
        self._load_plugins()

    def _load_plugins(self) -> None:
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):
            selected = eps.select(group=PREDICTOR_ENTRY_POINT)
        else:
            selected = [ep for ep in eps if ep.group == PREDICTOR_ENTRY_POINT]
        for entry_point in selected:
            try:
                predictor_cls = entry_point.load()
                self._predictors[entry_point.name] = predictor_cls
            except Exception as e:
                print(f"Failed to load predictor '{entry_point.name}': {e}")

    def get_predictor(self, name: str) -> Type[Any]:
        return self._predictors.get(name)

    def list_predictors(self) -> list[str]:
        return list(self._predictors.keys())


registry = PredictorRegistry()
