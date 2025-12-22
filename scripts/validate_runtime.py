#!/usr/bin/env python3
"""
Runtime Validation Script - Live API Validation

This script executes real HTTP requests against all public API endpoints
to validate runtime behavior, error handling, and data integrity.

Usage:
    python scripts/validate_runtime.py [--base-url http://localhost:8000]
"""

import json
import sys
import time
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "http://localhost:8000"


class ValidationResult:
    """Container for validation results."""

    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.success = False
        self.status_code: Optional[int] = None
        self.response_body: Optional[Dict] = None
        self.error: Optional[str] = None
        self.validation_errors: List[str] = []

    def record_success(self, status_code: int, body: Dict):
        """Record successful response."""
        self.success = True
        self.status_code = status_code
        self.response_body = body

    def record_error(self, status_code: int, error: str, body: Optional[Dict] = None):
        """Record error response."""
        self.success = False
        self.status_code = status_code
        self.error = error
        self.response_body = body

    def add_validation_error(self, message: str):
        """Add a validation error."""
        self.validation_errors.append(message)

    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "success": self.success,
            "status_code": self.status_code,
            "error": self.error,
            "validation_errors": self.validation_errors,
            "response_sample": (
                json.dumps(self.response_body)[:200] if self.response_body else None
            ),
        }


def validate_health_endpoint() -> ValidationResult:
    """Validate /health endpoint."""
    result = ValidationResult("/health", "GET")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        result.record_success(response.status_code, response.json())
        if response.status_code != 200:
            result.add_validation_error(f"Expected 200, got {response.status_code}")
        body = response.json()
        if "status" not in body or body["status"] != "ok":
            result.add_validation_error("Response missing 'status': 'ok'")
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_forecast_endpoint_valid() -> ValidationResult:
    """Validate POST /api/forecast with valid request."""
    result = ValidationResult("/api/forecast", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=30)
        if response.status_code == 200:
            body = response.json()
            result.record_success(response.status_code, body)
            # Validate structure
            required_fields = ["history", "forecast", "sources", "metadata"]
            for field in required_fields:
                if field not in body:
                    result.add_validation_error(f"Missing required field: {field}")
            # Validate forecast length
            if (
                "forecast" in body
                and len(body["forecast"]) != payload["forecast_horizon"]
            ):
                result.add_validation_error(
                    f"Forecast length mismatch: expected {payload['forecast_horizon']}, "
                    f"got {len(body.get('forecast', []))}"
                )
        else:
            result.record_error(
                response.status_code,
                f"Unexpected status code: {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_forecast_endpoint_invalid_coords() -> ValidationResult:
    """Validate POST /api/forecast with invalid coordinates."""
    result = ValidationResult("/api/forecast (invalid coords)", "POST")
    payload = {
        "latitude": 100.0,  # Invalid: > 90
        "longitude": -74.0060,
        "region_name": "Invalid",
        "days_back": 30,
        "forecast_horizon": 7,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=10)
        if response.status_code == 422:
            result.record_success(response.status_code, response.json())
        else:
            result.record_error(
                response.status_code,
                f"Expected 422 for invalid coordinates, got {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_forecast_endpoint_boundary() -> ValidationResult:
    """Validate POST /api/forecast with boundary values."""
    result = ValidationResult("/api/forecast (boundary)", "POST")
    # Test minimum valid values (days_back must be >= 7 per API validation)
    payload = {
        "latitude": -90.0,
        "longitude": -180.0,
        "region_name": "Boundary Test",
        "days_back": 7,  # Minimum valid value
        "forecast_horizon": 1,  # Minimum
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=30)
        if response.status_code == 200:
            result.record_success(response.status_code, response.json())
        else:
            result.record_error(
                response.status_code,
                f"Boundary values should be valid, got {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_forecasting_regions() -> ValidationResult:
    """Validate GET /api/forecasting/regions."""
    result = ValidationResult("/api/forecasting/regions", "GET")
    try:
        response = requests.get(f"{BASE_URL}/api/forecasting/regions", timeout=10)
        if response.status_code == 200:
            body = response.json()
            result.record_success(response.status_code, body)
            if not isinstance(body, list):
                result.add_validation_error("Response should be a list")
            elif len(body) == 0:
                result.add_validation_error("Response list is empty")
            else:
                # Validate first region structure
                first = body[0]
                required_fields = [
                    "id",
                    "name",
                    "country",
                    "region_type",
                    "latitude",
                    "longitude",
                ]
                for field in required_fields:
                    if field not in first:
                        result.add_validation_error(
                            f"Missing required field in region: {field}"
                        )
        else:
            result.record_error(
                response.status_code,
                f"Unexpected status code: {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_error_missing_fields() -> ValidationResult:
    """Validate POST /api/forecast with missing required fields."""
    result = ValidationResult("/api/forecast (missing fields)", "POST")
    payload = {
        "region_name": "Test",
        # Missing latitude, longitude, days_back, forecast_horizon
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=10)
        # Accept both 400 and 422 as valid error responses for missing fields
        if response.status_code in [400, 422]:
            body = response.json()
            result.record_success(response.status_code, body)
            # Verify error message is actionable
            if "detail" not in body:
                result.add_validation_error("Error response missing 'detail' field")
            elif isinstance(body["detail"], list):
                # Pydantic validation errors
                missing_fields = [err.get("loc", []) for err in body["detail"]]
                if not missing_fields:
                    result.add_validation_error(
                        "Error detail does not specify missing fields"
                    )
        else:
            result.record_error(
                response.status_code,
                f"Expected 400 or 422 for missing fields, got {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_error_wrong_types() -> ValidationResult:
    """Validate POST /api/forecast with wrong types."""
    result = ValidationResult("/api/forecast (wrong types)", "POST")
    payload = {
        "latitude": "not_a_number",  # Should be float
        "longitude": -74.0060,
        "region_name": "Test",
        "days_back": "thirty",  # Should be int
        "forecast_horizon": 7,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=10)
        # Accept both 400 and 422 as valid error responses for wrong types
        if response.status_code in [400, 422]:
            body = response.json()
            result.record_success(response.status_code, body)
            # Verify error message is actionable (has detail field)
            if "detail" not in body:
                result.add_validation_error("Error response missing 'detail' field")
            elif isinstance(body["detail"], list):
                # Verify errors reference the problematic fields and indicate type issues
                error_fields = [
                    err.get("loc", [])
                    for err in body["detail"]
                    if isinstance(err, dict)
                ]
                if not error_fields:
                    result.add_validation_error(
                        "Type errors do not reference problematic fields"
                    )
                # Type errors with parsing indicators (float_parsing, int_parsing) are acceptable
        else:
            result.record_error(
                response.status_code,
                f"Expected 400 or 422 for wrong types, got {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_error_extreme_values() -> ValidationResult:
    """Validate POST /api/forecast with extreme values."""
    result = ValidationResult("/api/forecast (extreme values)", "POST")
    test_cases = [
        {
            "name": "max_lat_max_lon",
            "payload": {
                "latitude": 90.0,
                "longitude": 180.0,
                "region_name": "Extreme Test",
                "days_back": 365,  # Maximum
                "forecast_horizon": 30,  # Maximum
            },
            "expected_status": 200,
        },
        {
            "name": "exceeds_max_days_back",
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "region_name": "Test",
                "days_back": 366,  # Exceeds max
                "forecast_horizon": 7,
            },
            "expected_status": 422,
        },
        {
            "name": "exceeds_max_horizon",
            "payload": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "region_name": "Test",
                "days_back": 30,
                "forecast_horizon": 31,  # Exceeds max
            },
            "expected_status": 422,
        },
    ]

    all_passed = True
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/forecast", json=test_case["payload"], timeout=10
            )
            if response.status_code != test_case["expected_status"]:
                result.add_validation_error(
                    f"{test_case['name']}: Expected {test_case['expected_status']}, "
                    f"got {response.status_code}"
                )
                all_passed = False
        except Exception as e:
            result.add_validation_error(f"{test_case['name']}: Exception: {str(e)}")
            all_passed = False

    if all_passed:
        result.record_success(200, {"extreme_value_tests": "all_passed"})
    else:
        result.record_error(0, "Some extreme value tests failed")
    return result


def validate_error_empty_payload() -> ValidationResult:
    """Validate POST /api/forecast with empty payload."""
    result = ValidationResult("/api/forecast (empty payload)", "POST")
    payload = {}
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=10)
        if response.status_code == 422:
            body = response.json()
            result.record_success(response.status_code, body)
        else:
            result.record_error(
                response.status_code,
                f"Expected 422 for empty payload, got {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_error_extra_fields() -> ValidationResult:
    """Validate POST /api/forecast with unexpected extra fields."""
    result = ValidationResult("/api/forecast (extra fields)", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "Test",
        "days_back": 30,
        "forecast_horizon": 7,
        "unexpected_field": "should_be_ignored",
        "another_extra": 12345,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=30)
        # Extra fields should be ignored (Pydantic default behavior)
        if response.status_code == 200:
            body = response.json()
            result.record_success(response.status_code, body)
            # Verify request was processed correctly despite extra fields
            if "history" not in body or "forecast" not in body:
                result.add_validation_error("Response missing required fields")
        elif response.status_code == 422:
            # If extra fields cause validation error, that's also acceptable
            body = response.json()
            result.record_success(response.status_code, body)
        else:
            result.record_error(
                response.status_code,
                f"Unexpected status code: {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_data_integrity() -> ValidationResult:
    """Validate data integrity of forecast response."""
    result = ValidationResult("/api/forecast (data integrity)", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=30)
        if response.status_code == 200:
            body = response.json()
            result.record_success(response.status_code, body)

            # Check for NaN, inf, or None in numeric fields
            def check_value(value: Any, path: str):
                """Recursively check for invalid numeric values."""
                if isinstance(value, float):
                    if value != value:  # NaN check
                        result.add_validation_error(f"NaN found at {path}")
                    if value == float("inf") or value == float("-inf"):
                        result.add_validation_error(f"Inf found at {path}")
                elif isinstance(value, dict):
                    for k, v in value.items():
                        check_value(v, f"{path}.{k}")
                elif isinstance(value, list):
                    for i, v in enumerate(value):
                        check_value(v, f"{path}[{i}]")

            check_value(body, "root")

            # Validate behavior_index range [0.0, 1.0]
            if "history" in body:
                for i, item in enumerate(body["history"]):
                    if "behavior_index" in item:
                        bi = item["behavior_index"]
                        if not (0.0 <= bi <= 1.0):
                            result.add_validation_error(
                                f"behavior_index out of range [0.0, 1.0]: {bi} at history[{i}]"
                            )

            if "forecast" in body:
                for i, item in enumerate(body["forecast"]):
                    if "behavior_index" in item:
                        bi = item["behavior_index"]
                        if not (0.0 <= bi <= 1.0):
                            result.add_validation_error(
                                f"behavior_index out of range [0.0, 1.0]: {bi} at forecast[{i}]"
                            )

        else:
            result.record_error(
                response.status_code,
                f"Failed to get forecast for integrity check: {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_resilience_partial_data() -> ValidationResult:
    """Validate system resilience when data sources return partial/empty data."""
    result = ValidationResult("/api/forecast (resilience)", "POST")
    # Test with valid request - system should handle gracefully even if some
    # data sources are unavailable (they default to 0.5)
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }
    try:
        response = requests.post(f"{BASE_URL}/api/forecast", json=payload, timeout=30)
        if response.status_code == 200:
            body = response.json()
            result.record_success(response.status_code, body)
            # Verify system doesn't crash on partial data
            # Missing data sources should default to 0.5 (system behavior)
            if "history" not in body or len(body.get("history", [])) == 0:
                result.add_validation_error("System returned empty history")
            # Verify no 500 errors (system should degrade gracefully)
        elif response.status_code == 500:
            result.record_error(
                response.status_code,
                "System returned 500 on partial data (should degrade gracefully)",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
        else:
            result.record_error(
                response.status_code,
                f"Unexpected status code: {response.status_code}",
                (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_load_sequential_requests() -> ValidationResult:
    """Validate system under sequential load (10 requests)."""
    result = ValidationResult("/api/forecast (load test)", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }

    timings = []
    status_codes = []
    response_hashes = []

    try:
        for i in range(10):
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/api/forecast", json=payload, timeout=30
            )
            elapsed = time.time() - start_time
            timings.append(elapsed)
            status_codes.append(response.status_code)

            if response.status_code == 200:
                body = response.json()
                # Create a simple hash of response structure for consistency check
                response_hash = hash(
                    (
                        len(body.get("history", [])),
                        len(body.get("forecast", [])),
                        len(body.get("sources", [])),
                    )
                )
                response_hashes.append(response_hash)
            else:
                response_hashes.append(None)

        # Analyze results
        if all(code == 200 for code in status_codes):
            result.record_success(200, {"load_test": "passed"})
            # Check for state bleed (responses should be consistent)
            if len(set(response_hashes)) > 1:
                result.add_validation_error(
                    "Response structure inconsistent across requests (possible state bleed)"
                )
            # Check timing (should be reasonable, not exponentially increasing)
            if max(timings) > min(timings) * 10:
                result.add_validation_error(
                    f"Response time variance too high: min={min(timings):.2f}s, "
                    f"max={max(timings):.2f}s"
                )
            # Record timing stats
            result.response_body = {
                "timings": {
                    "min": min(timings),
                    "max": max(timings),
                    "avg": sum(timings) / len(timings),
                    "all": timings,
                },
                "all_succeeded": True,
                "response_consistent": len(set(response_hashes)) == 1,
            }
        else:
            result.record_error(
                0,
                f"Some requests failed: status codes {status_codes}",
                {
                    "status_codes": status_codes,
                    "timings": timings,
                },
            )
    except Exception as e:
        result.record_error(0, str(e))
    return result


def main():
    """Run all validations."""
    global BASE_URL
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]

    print(f"Runtime Validation - Base URL: {BASE_URL}")
    print("=" * 70)

    results: List[ValidationResult] = []

    # Core endpoints
    print("\n1. Validating /health endpoint...")
    results.append(validate_health_endpoint())

    print("\n2. Validating /api/forecast (valid request)...")
    results.append(validate_forecast_endpoint_valid())

    print("\n3. Validating /api/forecast (invalid coordinates)...")
    results.append(validate_forecast_endpoint_invalid_coords())

    print("\n4. Validating /api/forecast (boundary values)...")
    results.append(validate_forecast_endpoint_boundary())

    print("\n5. Validating /api/forecasting/regions...")
    results.append(validate_forecasting_regions())

    print("\n6. Validating data integrity...")
    results.append(validate_data_integrity())

    # Error semantics tests
    print("\n7. Validating error semantics (missing fields)...")
    results.append(validate_error_missing_fields())

    print("\n8. Validating error semantics (wrong types)...")
    results.append(validate_error_wrong_types())

    print("\n9. Validating error semantics (extreme values)...")
    results.append(validate_error_extreme_values())

    print("\n10. Validating error semantics (empty payload)...")
    results.append(validate_error_empty_payload())

    print("\n11. Validating error semantics (extra fields)...")
    results.append(validate_error_extra_fields())

    # Resilience tests
    print("\n12. Validating resilience (partial data)...")
    results.append(validate_resilience_partial_data())

    # Load tests
    print("\n13. Validating load (10 sequential requests)...")
    results.append(validate_load_sequential_requests())

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r.success and not r.validation_errors)
    failed = len(results) - passed

    for result in results:
        status = "✓" if result.success and not result.validation_errors else "✗"
        print(f"{status} {result.method} {result.endpoint}")
        if result.validation_errors:
            for error in result.validation_errors:
                print(f"    ERROR: {error}")
        if result.error:
            print(f"    ERROR: {result.error}")

    print(f"\nPassed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")

    # Write detailed results to file
    output_file = "docs/reports/RUNTIME_VALIDATION_RESULTS.json"
    with open(output_file, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    print(f"\nDetailed results written to: {output_file}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
