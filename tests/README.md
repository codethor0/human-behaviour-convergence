# Tests

This folder contains unit tests and integration tests for the project.

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov --cov-report=html
```

## Structure

This directory contains 30 test files covering:
- API endpoints (`test_api_backend.py`, `test_forecasting_endpoints.py`, `test_live_endpoints.py`, `test_playground_endpoints.py`, `test_public_api.py`, `test_regions_api.py`)
- Core functionality (`test_behavior_index.py`, `test_forecasting.py`, `test_explanations.py`, `test_location_normalizer.py`, `test_forecast_config.py`)
- Connectors (`test_connectors.py`, `test_connectors_integration.py`, `test_economic_fred.py`, `test_gdelt_connector.py`, `test_mobility_connector.py`, `test_owid_connector.py`, `test_public_health_connector.py`, `test_search_trends_connector.py`, `test_usgs_connector.py`)
- Services (`test_intelligence_layer.py`, `test_live_monitor.py`, `test_playground.py`, `test_storage_db.py`, `test_subindex_details.py`, `test_visualization_layer.py`)
- CLI (`test_cli.py`)
- Governance (`test_governance_invariants.py`)
- Utilities (`test_no_emoji_script.py`)

## CI

Tests are automatically run on every push via GitHub Actions.
See `.github/workflows/ci.yml`.
