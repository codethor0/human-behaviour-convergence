#!/usr/bin/env python3
"""Test location normalization fixes - run after installing dependencies."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH for imports
import os

os.environ["PYTHONPATH"] = str(project_root)

try:
    from app.core.forecast_config import ForecastConfigBuilder
    from app.core.location_normalizer import LocationNormalizer
except ImportError as e:
    print(f"ERROR: Could not import modules. Make sure dependencies are installed:")
    print(f"  pip install -r requirements.txt")
    print(f"  pip install -r requirements-dev.txt")
    print(f"\nImport error: {e}")
    sys.exit(1)


def test_ambiguous_washington():
    """Test ambiguous Washington case."""
    print("=" * 70)
    print("TEST 1: Ambiguous Washington Case")
    print("=" * 70)

    normalizer = LocationNormalizer()
    result = normalizer.normalize("Event happened near Washington")

    print(f"\nInput: 'Event happened near Washington'")
    print(f"\nOutput:")
    print(f"  normalized_location: {result.normalized_location}")
    print(f"  best_guess_region_id: {result.best_guess_region_id}")
    print(f"  alternate_region_ids: {result.alternate_region_ids}")
    print(f"  ambiguity_reason: {result.ambiguity_reason}")

    # Verify
    assert (
        result.normalized_location is None
    ), "❌ Should NOT create normalized_location for ambiguous case"
    assert (
        result.best_guess_region_id == "us_wa"
    ), f"❌ Expected 'us_wa', got '{result.best_guess_region_id}'"
    assert result.alternate_region_ids == [
        "us_dc"
    ], f"❌ Expected ['us_dc'], got {result.alternate_region_ids}"
    assert result.ambiguity_reason is not None, "❌ Should have ambiguity_reason"
    assert (
        "Ambiguous" in result.ambiguity_reason
    ), f"❌ Reason should mention 'Ambiguous'"

    print("\n✅ PASS: Ambiguous Washington handled correctly")
    return True


def test_dc_context():
    """Test DC context case."""
    print("\n" + "=" * 70)
    print("TEST 2: DC Context Case")
    print("=" * 70)

    normalizer = LocationNormalizer()
    result = normalizer.normalize("Event happened near Washington D.C.")

    print(f"\nInput: 'Event happened near Washington D.C.'")
    print(f"\nOutput:")
    if result.normalized_location:
        print(
            f"  normalized_location.region_id: {result.normalized_location.region_id}"
        )
        print(
            f"  normalized_location.region_label: {result.normalized_location.region_label}"
        )
    else:
        print(f"  normalized_location: None")

    assert (
        result.normalized_location is not None
    ), "❌ Should create normalized_location for DC context"
    assert (
        result.normalized_location.region_id == "us_dc"
    ), f"❌ Expected 'us_dc', got '{result.normalized_location.region_id}'"

    print("\n✅ PASS: DC context handled correctly")
    return True


def test_wa_state_context():
    """Test WA state context case."""
    print("\n" + "=" * 70)
    print("TEST 3: WA State Context Case")
    print("=" * 70)

    normalizer = LocationNormalizer()
    result = normalizer.normalize("Event in Seattle, Washington")

    print(f"\nInput: 'Event in Seattle, Washington'")
    print(f"\nOutput:")
    if result.normalized_location:
        print(
            f"  normalized_location.region_id: {result.normalized_location.region_id}"
        )
        print(
            f"  normalized_location.region_label: {result.normalized_location.region_label}"
        )
    else:
        print(f"  normalized_location: None")

    assert (
        result.normalized_location is not None
    ), "❌ Should create normalized_location for WA state context"
    assert (
        result.normalized_location.region_id == "us_wa"
    ), f"❌ Expected 'us_wa', got '{result.normalized_location.region_id}'"

    print("\n✅ PASS: WA state context handled correctly")
    return True


def test_forecast_config_ambiguity():
    """Test ForecastConfigBuilder handles ambiguity correctly."""
    print("\n" + "=" * 70)
    print("TEST 4: ForecastConfigBuilder Ambiguity Handling")
    print("=" * 70)

    builder = ForecastConfigBuilder()
    config = builder.prepare_config(description="Event happened near Washington")

    print(f"\nInput: 'Event happened near Washington'")
    print(f"\nOutput:")
    print(f"  normalized_location exists: {config.normalized_location is not None}")
    if config.normalized_location:
        print(
            f"  normalized_location.region_id: {config.normalized_location.region_id}"
        )
        print(
            f"  normalized_location.best_guess: {config.normalized_location.best_guess}"
        )
        print(
            f"  normalized_location.alternatives: {config.normalized_location.alternatives}"
        )

    assert (
        config.normalized_location is not None
    ), "❌ ForecastConfigBuilder should create normalized_location"
    assert (
        config.normalized_location.best_guess is True
    ), "❌ Should have best_guess=True for ambiguous case"
    assert (
        len(config.normalized_location.alternatives) > 0
    ), "❌ Should have alternatives"
    assert config.normalized_location.region_id in [
        "us_wa",
        "us_dc",
    ], f"❌ region_id should be us_wa or us_dc"

    print("\n✅ PASS: ForecastConfigBuilder handles ambiguity correctly")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LOCATION NORMALIZATION FIX VERIFICATION")
    print("=" * 70)

    try:
        test_ambiguous_washington()
        test_dc_context()
        test_wa_state_context()
        test_forecast_config_ambiguity()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nLocation normalization is working correctly.")
        print("You can now start the backend server to test via API.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
