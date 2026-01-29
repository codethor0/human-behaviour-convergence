# SPDX-License-Identifier: PROPRIETARY
"""Tests for Grafana dashboard JSON files."""
import json
from pathlib import Path

import pytest


class TestGrafanaDashboards:
    """Test Grafana dashboard JSON files."""

    @pytest.fixture
    def dashboards_dir(self):
        """Get dashboards directory."""
        return Path(__file__).parent.parent / "infra" / "grafana" / "dashboards"

    def test_all_dashboards_are_valid_json(self, dashboards_dir):
        """Test that all dashboard JSON files are valid JSON."""
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        json_files = list(dashboards_dir.glob("*.json"))
        assert len(json_files) > 0, "No dashboard JSON files found"

        for json_file in json_files:
            with open(json_file, "r") as f:
                try:
                    data = json.load(f)
                    assert isinstance(
                        data, dict
                    ), f"{json_file.name} is not a JSON object"
                except json.JSONDecodeError as e:
                    pytest.fail(f"{json_file.name} is not valid JSON: {e}")

    def test_dashboards_have_required_fields(self, dashboards_dir):
        """Test that dashboards have required Grafana fields."""
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        required_fields = ["title", "uid", "schemaVersion", "panels"]

        for json_file in dashboards_dir.glob("*.json"):
            with open(json_file, "r") as f:
                data = json.load(f)

                for field in required_fields:
                    assert (
                        field in data
                    ), f"{json_file.name} missing required field: {field}"

    def test_model_performance_dashboard_queries(self, dashboards_dir):
        """Test that model performance dashboard uses correct metrics."""
        dashboard_file = dashboards_dir / "model_performance.json"

        if not dashboard_file.exists():
            pytest.skip("model_performance.json not found")

        with open(dashboard_file, "r") as f:
            data = json.load(f)

        # Check that it queries model metrics
        dashboard_str = json.dumps(data)
        assert "hbc_model_mae" in dashboard_str
        assert "hbc_model_rmse" in dashboard_str
        assert "hbc_model_mape" in dashboard_str
        assert "hbc_interval_coverage" in dashboard_str
        assert "hbc_backtest_last_run_timestamp_seconds" in dashboard_str

        # Check that it doesn't use the old incorrect metric
        assert "hbc_model_selected_total" not in dashboard_str

    def test_forecast_quality_drift_dashboard_queries(self, dashboards_dir):
        """Test that forecast quality drift dashboard uses model-specific metrics."""
        dashboard_file = dashboards_dir / "forecast_quality_drift.json"

        if not dashboard_file.exists():
            pytest.skip("forecast_quality_drift.json not found")

        with open(dashboard_file, "r") as f:
            data = json.load(f)

        dashboard_str = json.dumps(data)

        # Check for model-specific metrics
        assert "hbc_forecast_compute_duration_seconds" in dashboard_str
        assert "hbc_interval_coverage" in dashboard_str
        assert "hbc_backtest_last_run_timestamp_seconds" in dashboard_str
        assert "hbc_forecast_total" in dashboard_str

        # Check for model variable
        assert '"name": "model"' in dashboard_str or '"name":"model"' in dashboard_str

    def test_baselines_dashboard_queries(self, dashboards_dir):
        """Test that baselines dashboard queries baseline models."""
        dashboard_file = dashboards_dir / "baselines.json"

        if not dashboard_file.exists():
            pytest.skip("baselines.json not found")

        with open(dashboard_file, "r") as f:
            data = json.load(f)

        # Collect all expr strings from panels (loaded JSON has unescaped quotes)
        exprs = []
        for panel in data.get("panels", []):
            for target in panel.get("targets", []):
                if "expr" in target:
                    exprs.append(target["expr"])
        combined = " ".join(exprs)
        # Should query naive and seasonal_naive models
        assert 'model="naive"' in combined or "model='naive'" in combined
        assert (
            'model="seasonal_naive"' in combined or "model='seasonal_naive'" in combined
        )

    def test_classical_models_dashboard_queries(self, dashboards_dir):
        """Test that classical models dashboard queries statistical models."""
        dashboard_file = dashboards_dir / "classical_models.json"

        if not dashboard_file.exists():
            pytest.skip("classical_models.json not found")

        with open(dashboard_file, "r") as f:
            data = json.load(f)

        dashboard_str = json.dumps(data)

        # Should query exponential_smoothing and arima
        assert (
            "exponential_smoothing" in dashboard_str
            or "exponential" in dashboard_str.lower()
        )
        # ARIMA may or may not be present depending on availability

    def test_dashboards_have_valid_uids(self, dashboards_dir):
        """Test that all dashboards have valid UIDs."""
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        uids = set()

        for json_file in dashboards_dir.glob("*.json"):
            with open(json_file, "r") as f:
                data = json.load(f)

                if "uid" in data:
                    uid = data["uid"]
                    assert isinstance(
                        uid, str
                    ), f"{json_file.name} UID must be a string"
                    assert len(uid) > 0, f"{json_file.name} UID cannot be empty"
                    assert uid not in uids, f"Duplicate UID found: {uid}"
                    uids.add(uid)

    def test_dashboards_have_panels(self, dashboards_dir):
        """Test that all dashboards have at least one panel."""
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        for json_file in dashboards_dir.glob("*.json"):
            with open(json_file, "r") as f:
                data = json.load(f)

                assert "panels" in data, f"{json_file.name} missing panels"
                assert isinstance(
                    data["panels"], list
                ), f"{json_file.name} panels must be a list"
                assert (
                    len(data["panels"]) > 0
                ), f"{json_file.name} must have at least one panel"
