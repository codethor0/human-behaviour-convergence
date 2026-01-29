# Write Your First Predictor in 15 Minutes

This guide walks you through creating a custom predictor plugin for the Human Behaviour Convergence forecasting system.

## What is a Predictor?

A predictor is a Python class that implements a forecasting model. The system automatically discovers and loads predictors via entry points, allowing you to extend forecasting capabilities without modifying core code.

## Step-by-Step Guide

### Step 1: Create Your Predictor Class (5 minutes)

Create a new file in the `predictors/` directory:

```python
# predictors/my_predictor.py
import pandas as pd
from typing import Dict, List, Any

class MyPredictor:
    """
    A simple moving average predictor.

    This predictor calculates a moving average of the behavioral index
    and uses it as the forecast.
    """

    def __init__(self, window: int = 7):
        """
        Initialize the predictor.

        Args:
            window: Number of days for moving average window
        """
        self.window = window

    def predict(
        self,
        historical_data: pd.DataFrame,
        forecast_horizon: int = 7
    ) -> Dict[str, Any]:
        """
        Generate a forecast from historical data.

        Args:
            historical_data: DataFrame with columns ['timestamp', 'behavior_index']
            forecast_horizon: Number of days to forecast ahead

        Returns:
            Dictionary with 'forecast' (list of predictions) and metadata
        """
        if len(historical_data) < self.window:
            # Fallback: use last value
            last_value = historical_data['behavior_index'].iloc[-1]
            forecast = [last_value] * forecast_horizon
        else:
            # Calculate moving average
            ma = historical_data['behavior_index'].rolling(
                window=self.window
            ).mean().iloc[-1]
            forecast = [ma] * forecast_horizon

        return {
            'forecast': forecast,
            'model_type': 'MovingAverage',
            'window': self.window,
            'horizon': forecast_horizon
        }
```

### Step 2: Register Your Predictor (2 minutes)

Add an entry point in `pyproject.toml`:

```toml
[project.entry-points."human_behaviour_predictor"]
my_predictor = "predictors.my_predictor:MyPredictor"
```

After adding the entry point, reinstall the package:

```bash
pip install -e .
```

### Step 3: Test Your Predictor (5 minutes)

Create a test script:

```python
# test_my_predictor.py
import pandas as pd
from datetime import datetime, timedelta
from predictors.my_predictor import MyPredictor

# Create sample historical data
dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
data = pd.DataFrame({
    'timestamp': dates,
    'behavior_index': [0.5 + 0.1 * (i % 10) / 10 for i in range(30)]
})

# Initialize and test
predictor = MyPredictor(window=7)
result = predictor.predict(data, forecast_horizon=7)

print(f"Forecast: {result['forecast']}")
print(f"Model: {result['model_type']}")
```

Run it:

```bash
python test_my_predictor.py
```

### Step 4: Use the Registry (3 minutes)

The system automatically discovers your predictor:

```python
from predictors.registry import registry

# List all available predictors
print(registry.list_predictors())
# Output: ['example', 'my_predictor']

# Get your predictor
PredictorClass = registry.get_predictor('my_predictor')
predictor = PredictorClass(window=7)

# Use it
result = predictor.predict(historical_data, forecast_horizon=7)
```

## Predictor Interface

Your predictor class should implement:

- `__init__(self, **kwargs)`: Constructor with configurable parameters
- `predict(self, historical_data: pd.DataFrame, forecast_horizon: int) -> Dict[str, Any]`: Main prediction method

### Input Format

`historical_data` is a pandas DataFrame with:
- `timestamp`: datetime index or column
- `behavior_index`: float values (0.0 to 1.0)

### Output Format

Return a dictionary with:
- `forecast`: List of float predictions (length = forecast_horizon)
- `model_type`: String identifier for your model
- Additional metadata (optional)

## Example: Exponential Smoothing Predictor

See `predictors/example_predictor.py` for a complete example using exponential smoothing.

## Template Repository

For a standalone predictor project, create your own repository based on this project's structure.

## Contributing

1. Fork this repository or use the template
2. Create your predictor class
3. Add entry point to `pyproject.toml`
4. Write tests in `tests/test_*_predictor.py`
5. Open a PR with the `community` label

## Next Steps

- Check [app-plan.md](../app-plan.md) for architecture details
- Join discussions in GitHub Issues with the `community` label

---

**Time check:** If you followed along, you should have a working predictor in about 15 minutes!
