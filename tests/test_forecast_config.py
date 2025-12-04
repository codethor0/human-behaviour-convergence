# SPDX-License-Identifier: PROPRIETARY
"""Tests for forecast configuration preparation."""

from app.core.forecast_config import ForecastConfigBuilder, prepare_forecast_config


class TestForecastConfigBuilder:
    """Test forecast configuration building."""

    def test_west_virginia_guardsmen_incident(self):
        """Test West Virginia Guardsmen incident location normalization."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(
            description=(
                "Two West Virginia National Guardsmen were shot near the "
                "White House in Washington, D.C."
            )
        )

        assert config.normalized_location is not None
        assert config.normalized_location.region_id == "us_dc"
        assert config.normalized_location.region_label == "District of Columbia"
        assert config.normalized_location.state_like_label == "District of Columbia"
        assert config.normalized_location.state_code == "DC"
        assert config.normalized_location.admin_level == "district"
        assert config.normalized_location.best_guess is False
        # Reason should mention D.C. or federal buildings
        assert (
            "d.c" in config.normalized_location.reason.lower()
            or "federal" in config.normalized_location.reason.lower()
        )

    def test_washington_state_from_city(self):
        """Test Washington state from city context."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(description="Event in Seattle, Washington")

        assert config.normalized_location is not None
        assert config.normalized_location.region_id == "us_wa"
        assert config.normalized_location.state_like_label == "Washington"
        assert config.normalized_location.state_code == "WA"
        assert config.normalized_location.admin_level == "state"

    def test_user_selected_region_id(self):
        """Test explicit user selection takes precedence."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(
            description="Some event", user_selected_region_id="us_mn"
        )

        assert config.normalized_location is not None
        assert config.normalized_location.region_id == "us_mn"
        assert config.normalized_location.region_label == "Minnesota"
        assert config.normalized_location.state_code == "MN"
        assert config.normalized_location.admin_level == "state"

    def test_city_region(self):
        """Test city-level region configuration."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(description="Protest near Times Square")

        assert config.normalized_location is not None
        assert config.normalized_location.region_id == "city_nyc"
        assert config.normalized_location.region_label == "New York City"
        assert config.normalized_location.state_like_label == "New York"
        assert config.normalized_location.state_code == "NY"
        assert config.normalized_location.admin_level == "city"

    def test_forecast_request_structure(self):
        """Test forecast request is properly structured."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(
            description="Event in California",
            historical_days=180,
            forecast_horizon_days=14,
        )

        assert config.forecast_request is not None
        assert config.forecast_request["region_id"] == "us_ca"
        assert config.forecast_request["historical_days"] == 180
        assert config.forecast_request["forecast_horizon_days"] == 14

    def test_ambiguity_handling(self):
        """Test ambiguous locations are handled with alternatives."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(description="Event happened near Washington")

        assert config.normalized_location is not None
        # Should have best_guess=True and alternatives
        if config.normalized_location.best_guess:
            assert len(config.normalized_location.alternatives) > 0
            assert config.normalized_location.region_id in ["us_wa", "us_dc"]

    def test_convenience_function(self):
        """Test the convenience function."""
        config_dict = prepare_forecast_config(
            "Two West Virginia National Guardsmen were shot near the "
            "White House in Washington, D.C."
        )

        assert config_dict["task"] == "prepare_forecast_location_config"
        assert config_dict["normalized_location"]["region_id"] == "us_dc"
        assert config_dict["forecast_request"]["region_id"] == "us_dc"

    def test_state_code_mapping(self):
        """Test state codes are correctly mapped."""
        builder = ForecastConfigBuilder()

        # Test a few states
        test_cases = [
            ("Event in California", "us_ca", "CA"),
            ("Event in Texas", "us_tx", "TX"),
            ("Event in New York state", "us_ny", "NY"),
            ("Event in District of Columbia", "us_dc", "DC"),
        ]

        for description, expected_region_id, expected_code in test_cases:
            config = builder.prepare_config(description=description)
            assert config.normalized_location.region_id == expected_region_id
            assert config.normalized_location.state_code == expected_code

    def test_global_city(self):
        """Test global city configuration."""
        builder = ForecastConfigBuilder()
        config = builder.prepare_config(description="Event in Tokyo")

        assert config.normalized_location is not None
        assert config.normalized_location.region_id == "city_tokyo"
        assert config.normalized_location.admin_level == "city"
        # Non-US cities don't have state codes
        assert config.normalized_location.state_code is None
