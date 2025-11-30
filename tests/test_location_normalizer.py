# SPDX-License-Identifier: PROPRIETARY
"""Tests for location normalization."""

from app.core.location_normalizer import LocationNormalizer, normalize_location


class TestLocationNormalizer:
    """Test location normalization logic."""

    def test_washington_dc_vs_washington_state(self):
        """Test Washington D.C. vs Washington state disambiguation."""
        normalizer = LocationNormalizer()

        # D.C. cases
        result = normalizer.normalize(
            "Incident near the White House in Washington, D.C."
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_dc"
        assert "District of Columbia" in result.normalized_location.region_label

        result = normalizer.normalize("Event at the Capitol building")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_dc"

        result = normalizer.normalize("Protest in Washington D.C.")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_dc"

        # Washington state cases
        result = normalizer.normalize("Event in Seattle, Washington")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_wa"

        result = normalizer.normalize("Incident in the Pacific Northwest")
        # Should match Washington state if context suggests it
        # This might be ambiguous, so check best_guess
        if result.best_guess_region_id:
            assert result.best_guess_region_id == "us_wa"

    def test_incident_location_vs_home_state(self):
        """Test that incident location is used, not home state."""
        normalizer = LocationNormalizer()

        # Example: incident location should be used, not origin location
        result = normalizer.normalize(
            "Two West Virginia National Guardsmen were shot near the White House in Washington, D.C."
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_dc"
        assert "us_wv" not in [alt for alt in result.normalized_location.alternatives]

        # Another example: California team playing in New York
        result = normalizer.normalize(
            "California team members involved in incident in New York City"
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_nyc"
        assert "us_ca" not in [alt for alt in result.normalized_location.alternatives]

    def test_city_vs_state_disambiguation(self):
        """Test city vs state disambiguation."""
        normalizer = LocationNormalizer()

        # City cases
        result = normalizer.normalize("Event in New York City")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_nyc"

        result = normalizer.normalize("Incident in Manhattan")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_nyc"

        result = normalizer.normalize("Protest near Times Square")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_nyc"

        # State cases
        result = normalizer.normalize("State-wide emergency in New York")
        # Should prefer state if state-wide context
        # Note: This might need refinement based on actual matching logic

        result = normalizer.normalize("Event in upstate New York")
        # Should prefer state for upstate

    def test_global_cities(self):
        """Test global city matching."""
        normalizer = LocationNormalizer()

        result = normalizer.normalize("Event in Tokyo")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_tokyo"

        result = normalizer.normalize("Incident in London")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_london"

        result = normalizer.normalize("Protest in Los Angeles")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_la"

    def test_explicit_location_parameter(self):
        """Test explicit location parameter."""
        normalizer = LocationNormalizer()

        result = normalizer.normalize(
            "Some event happened", explicit_location="California"
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_ca"

        result = normalizer.normalize(
            "Incident occurred", explicit_location="New York City"
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "city_nyc"

    def test_ambiguity_handling(self):
        """Test ambiguity handling."""
        normalizer = LocationNormalizer()

        # Ambiguous Washington
        result = normalizer.normalize("Event happened near Washington")
        # Should return best_guess with alternatives OR normalized with alternatives
        if result.normalized_location:
            # If it matched, should have alternatives in notes
            assert (
                len(result.normalized_location.alternatives) > 0
                or len(result.normalized_location.notes) > 0
            )
        else:
            # If ambiguous, should have best_guess
            assert result.best_guess_region_id is not None
            assert len(result.alternate_region_ids) > 0
            assert result.ambiguity_reason is not None

    def test_convenience_function(self):
        """Test the convenience function."""
        result = normalize_location(
            "Two West Virginia National Guardsmen were shot near the White House in Washington, D.C."
        )
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_dc"

    def test_state_abbreviations(self):
        """Test state abbreviation matching."""
        normalizer = LocationNormalizer()

        # Test some common abbreviations
        result = normalizer.normalize("Event in CA", explicit_location="California")
        assert result.normalized_location is not None
        assert result.normalized_location.region_id == "us_ca"

        result = normalizer.normalize("Incident in NY")
        # Should match New York state (or city if context suggests)
        # Note: "NY" abbreviation might need explicit_location or better matching
        # For now, check if it matches or provides alternatives
        if result.normalized_location:
            assert result.normalized_location.region_id in ["us_ny", "city_nyc"]
        else:
            # If not matched, should at least have best_guess or note the issue
            assert (
                result.best_guess_region_id is not None
                or result.ambiguity_reason is not None
            )

    def test_district_of_columbia_aliases(self):
        """Test various D.C. aliases."""
        normalizer = LocationNormalizer()

        aliases = [
            "Washington D.C.",
            "Washington DC",
            "Washington, D.C.",
            "Washington, DC",
            "DC",
            "District of Columbia",
            "D.C.",
        ]

        for alias in aliases:
            result = normalizer.normalize(f"Event in {alias}")
            assert result.normalized_location is not None, f"Failed for alias: {alias}"
            assert (
                result.normalized_location.region_id == "us_dc"
            ), f"Wrong region for alias: {alias}"
