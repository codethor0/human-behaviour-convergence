# SPDX-License-Identifier: PROPRIETARY
"""Tests for explanation generation."""

from app.core.explanations import generate_explanation


class TestGenerateExplanation:
    """Test explanation generation."""

    def test_generate_explanation_basic(self):
        """Test basic explanation generation."""
        sub_indices = {
            "economic_stress": 0.3,
            "environmental_stress": 0.4,
            "mobility_activity": 0.7,
            "digital_attention": 0.5,
            "public_health_stress": 0.3,
        }

        explanation = generate_explanation(
            behavior_index=0.4,
            sub_indices=sub_indices,
        )

        assert "summary" in explanation
        assert "subindices" in explanation
        assert len(explanation["subindices"]) == 5
        assert "economic_stress" in explanation["subindices"]
        assert "environmental_stress" in explanation["subindices"]
        assert "mobility_activity" in explanation["subindices"]
        assert "digital_attention" in explanation["subindices"]
        assert "public_health_stress" in explanation["subindices"]

        # Check structure of sub-index explanations
        economic = explanation["subindices"]["economic_stress"]
        assert "level" in economic
        assert economic["level"] in ["low", "moderate", "high"]
        assert "reason" in economic
        assert isinstance(economic["reason"], str)
        assert "components" in economic
        assert isinstance(economic["components"], list)

    def test_generate_explanation_with_components(self):
        """Test explanation generation with component details."""
        sub_indices = {
            "economic_stress": 0.6,
            "environmental_stress": 0.5,
            "mobility_activity": 0.5,
            "digital_attention": 0.5,
            "public_health_stress": 0.5,
        }

        subindex_details = {
            "economic_stress": {
                "value": 0.6,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "value": 0.7,
                        "weight": 0.4,
                        "source": "yfinance",
                    },
                    {
                        "id": "consumer_sentiment",
                        "label": "Consumer Sentiment",
                        "value": 0.5,
                        "weight": 0.3,
                        "source": "FRED",
                    },
                ],
            },
            "environmental_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "weather_discomfort",
                        "label": "Weather Discomfort",
                        "value": 0.5,
                        "weight": 0.7,
                        "source": "Open-Meteo",
                    },
                    {
                        "id": "earthquake_intensity",
                        "label": "Earthquake Intensity",
                        "value": 0.3,
                        "weight": 0.3,
                        "source": "USGS",
                    },
                ],
            },
            "digital_attention": {
                "value": 0.5,
                "components": [
                    {
                        "id": "search_interest",
                        "label": "Search Interest",
                        "value": 0.5,
                        "weight": 0.5,
                        "source": "search_trends_api",
                    },
                    {
                        "id": "gdelt_tone",
                        "label": "GDELT Tone",
                        "value": 0.5,
                        "weight": 0.5,
                        "source": "GDELT",
                    },
                ],
            },
            "public_health_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "health_risk_index",
                        "label": "Health Risk Index",
                        "value": 0.5,
                        "weight": 0.5,
                        "source": "public_health_api",
                    },
                    {
                        "id": "owid_health_stress",
                        "label": "OWID Health Stress",
                        "value": 0.5,
                        "weight": 0.5,
                        "source": "OWID",
                    },
                ],
            },
            "mobility_activity": {
                "value": 0.5,
                "components": [
                    {
                        "id": "mobility_index",
                        "label": "Mobility Index",
                        "value": 0.5,
                        "weight": 1.0,
                        "source": "mobility_api",
                    },
                ],
            },
        }

        explanation = generate_explanation(
            behavior_index=0.52,
            sub_indices=sub_indices,
            subindex_details=subindex_details,
            region_name="New York City",
        )

        assert "summary" in explanation
        assert (
            "New York City" in explanation["summary"]
            or "new york" in explanation["summary"].lower()
        )

        # Check that components are included
        economic = explanation["subindices"]["economic_stress"]
        assert len(economic["components"]) > 0
        assert any(c["id"] == "market_volatility" for c in economic["components"])

        environmental = explanation["subindices"]["environmental_stress"]
        assert len(environmental["components"]) > 0
        assert any(
            c["id"] == "earthquake_intensity" for c in environmental["components"]
        )

        digital = explanation["subindices"]["digital_attention"]
        assert len(digital["components"]) > 0
        assert any(c["id"] == "gdelt_tone" for c in digital["components"])

        health = explanation["subindices"]["public_health_stress"]
        assert len(health["components"]) > 0
        assert any("owid" in c["id"].lower() for c in health["components"])

    def test_generate_explanation_high_stress(self):
        """Test explanation for high stress scenario."""
        sub_indices = {
            "economic_stress": 0.8,
            "environmental_stress": 0.7,
            "mobility_activity": 0.2,
            "digital_attention": 0.9,
            "public_health_stress": 0.6,
        }

        explanation = generate_explanation(
            behavior_index=0.75,
            sub_indices=sub_indices,
        )

        assert (
            "high" in explanation["summary"].lower()
            or "disruption" in explanation["summary"].lower()
        )

        # Check that high stress sub-indices are marked as high
        assert explanation["subindices"]["economic_stress"]["level"] == "high"
        assert explanation["subindices"]["environmental_stress"]["level"] == "high"
        assert explanation["subindices"]["digital_attention"]["level"] == "high"

        # Mobility activity is inverted (low activity = high disruption)
        assert explanation["subindices"]["mobility_activity"]["level"] == "low"

    def test_generate_explanation_low_stress(self):
        """Test explanation for low stress scenario."""
        sub_indices = {
            "economic_stress": 0.2,
            "environmental_stress": 0.3,
            "mobility_activity": 0.8,
            "digital_attention": 0.2,
            "public_health_stress": 0.3,
        }

        explanation = generate_explanation(
            behavior_index=0.25,
            sub_indices=sub_indices,
        )

        assert (
            "low" in explanation["summary"].lower()
            or "stability" in explanation["summary"].lower()
        )

        # Check that low stress sub-indices are marked appropriately
        assert explanation["subindices"]["economic_stress"]["level"] in [
            "low",
            "moderate",
        ]
        assert explanation["subindices"]["environmental_stress"]["level"] in [
            "low",
            "moderate",
        ]
        assert explanation["subindices"]["digital_attention"]["level"] in [
            "low",
            "moderate",
        ]

        # Summary should reflect low stress
        assert (
            "low" in explanation["summary"].lower()
            or "stability" in explanation["summary"].lower()
        )

    def test_generate_explanation_deterministic(self):
        """Test that explanation generation is deterministic."""
        sub_indices = {
            "economic_stress": 0.5,
            "environmental_stress": 0.5,
            "mobility_activity": 0.5,
            "digital_attention": 0.5,
            "public_health_stress": 0.5,
        }

        explanation1 = generate_explanation(
            behavior_index=0.5,
            sub_indices=sub_indices,
        )

        explanation2 = generate_explanation(
            behavior_index=0.5,
            sub_indices=sub_indices,
        )

        # Should produce same results
        assert explanation1["summary"] == explanation2["summary"]
        assert explanation1["subindices"] == explanation2["subindices"]
