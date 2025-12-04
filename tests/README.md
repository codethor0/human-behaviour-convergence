# Tests

This folder contains unit tests and integration tests for the project.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Structure

- `test_forecasting.py` — Unit tests for forecasting pipeline
- `test_data_processing.py` — Tests for data loading and preprocessing
- `test_metrics.py` — Tests for evaluation metrics

## CI

Tests are automatically run on every push via GitHub Actions.
See `.github/workflows/test.yml`.
