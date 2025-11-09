# SPDX-License-Identifier: MIT-0
import pytest

from predictors.registry import PredictorRegistry


def test_registry_list_predictors():
    registry = PredictorRegistry()
    assert isinstance(registry.list_predictors(), list)


def test_registry_get_predictor_none():
    registry = PredictorRegistry()
    assert registry.get_predictor("nonexistent") is None
