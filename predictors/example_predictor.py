# SPDX-License-Identifier: MIT-0
from typing import Any

"""
Example predictor plugin for demonstration.
Implements a simple predict() method.
"""


class ExamplePredictor:
    def predict(self, data: Any) -> Any:
        # Dummy implementation: return input unchanged
        return data
