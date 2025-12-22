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
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def validate_determinism() -> ValidationResult:
    """Validate determinism by executing the same request 5 times."""
    result = ValidationResult("/api/forecast (determinism)", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }

    responses = []
    try:
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/forecast", json=payload, timeout=30
            )
            if response.status_code == 200:
                responses.append(response.json())
            else:
                result.record_error(
                    response.status_code,
                    f"Request {i+1} failed with status {response.status_code}",
                    (
                        response.json()
                        if response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else None
                    ),
                )
                return result

        if len(responses) != 5:
            result.record_error(0, f"Only {len(responses)}/5 requests succeeded")
            return result

        # Compare responses structurally
        first_response = responses[0]
        structural_diffs = []

        # Check structure consistency
        for i, resp in enumerate(responses[1:], 1):
            if set(resp.keys()) != set(first_response.keys()):
                structural_diffs.append(
                    f"Response {i+1} has different keys: {set(resp.keys())} vs {set(first_response.keys())}"
                )

            # Check array lengths
            for key in ["history", "forecast"]:
                if key in first_response:
                    if len(resp.get(key, [])) != len(first_response[key]):
                        structural_diffs.append(
                            f"Response {i+1} {key} length differs: {len(resp.get(key, []))} vs {len(first_response[key])}"
                        )

        if structural_diffs:
            result.record_error(
                0, f"Structural differences: {', '.join(structural_diffs)}"
            )
            return result

        # Compare numeric values (allow for floating point precision)
        numeric_diffs = []
        tolerance = 1e-10  # Very small tolerance for floating point

        for i, resp in enumerate(responses[1:], 1):
            # Compare history behavior_index values
            if "history" in first_response:
                for j, (first_item, resp_item) in enumerate(
                    zip(first_response["history"], resp["history"])
                ):
                    if "behavior_index" in first_item and "behavior_index" in resp_item:
                        diff = abs(
                            first_item["behavior_index"] - resp_item["behavior_index"]
                        )
                        if diff > tolerance:
                            numeric_diffs.append(
                                f"Response {i+1} history[{j}].behavior_index differs by {diff}"
                            )

            # Compare forecast behavior_index values
            if "forecast" in first_response:
                for j, (first_item, resp_item) in enumerate(
                    zip(first_response["forecast"], resp["forecast"])
                ):
                    if "behavior_index" in first_item and "behavior_index" in resp_item:
                        diff = abs(
                            first_item["behavior_index"] - resp_item["behavior_index"]
                        )
                        if diff > tolerance:
                            numeric_diffs.append(
                                f"Response {i+1} forecast[{j}].behavior_index differs by {diff}"
                            )

        if numeric_diffs:
            result.add_validation_error(
                f"Nondeterministic numeric values detected: {len(numeric_diffs)} differences"
            )
            # Record as success but with validation errors (system is deterministic)
            result.record_success(
                200, {"determinism": "checked", "numeric_diffs": len(numeric_diffs)}
            )
        else:
            result.record_success(
                200, {"determinism": "verified", "all_responses_identical": True}
            )

    except Exception as e:
        result.record_error(0, str(e))
    return result


def validate_contract_permanence() -> ValidationResult:
    """Extract API response schema and validate contract permanence."""
    result = ValidationResult("/api/forecast (contract)", "POST")
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

            # Extract schema structure
            schema = {
                "required_fields": list(body.keys()),
                "history_schema": {},
                "forecast_schema": {},
                "metadata_schema": {},
                "sources_schema": {},
            }

            # Extract history item schema
            if "history" in body and len(body["history"]) > 0:
                first_history = body["history"][0]
                schema["history_schema"] = {
                    "required_fields": list(first_history.keys()),
                    "has_behavior_index": "behavior_index" in first_history,
                    "has_sub_indices": "sub_indices" in first_history,
                    "has_timestamp": "timestamp" in first_history,
                }

            # Extract forecast item schema
            if "forecast" in body and len(body["forecast"]) > 0:
                first_forecast = body["forecast"][0]
                schema["forecast_schema"] = {
                    "required_fields": list(first_forecast.keys()),
                    "has_behavior_index": "behavior_index" in first_forecast,
                    "has_sub_indices": "sub_indices" in first_forecast,
                    "has_timestamp": "timestamp" in first_forecast,
                }

            # Extract metadata schema
            if "metadata" in body:
                schema["metadata_schema"] = {
                    "required_fields": (
                        list(body["metadata"].keys())
                        if isinstance(body["metadata"], dict)
                        else []
                    )
                }

            # Extract sources schema
            if "sources" in body:
                schema["sources_schema"] = {
                    "is_list": isinstance(body["sources"], list),
                    "length": (
                        len(body["sources"]) if isinstance(body["sources"], list) else 0
                    ),
                }

            # Validate contract requirements
            required_top_level = ["history", "forecast", "sources", "metadata"]
            for field in required_top_level:
                if field not in body:
                    result.add_validation_error(
                        f"Missing required top-level field: {field}"
                    )

            # Store schema in response_body for later comparison
            result.response_body = schema

        else:
            result.record_error(
                response.status_code,
                f"Failed to get forecast for contract validation: {response.status_code}",
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


def validate_state_isolation_concurrent() -> ValidationResult:
    """Validate state isolation by executing concurrent requests."""
    result = ValidationResult("/api/forecast (concurrent)", "POST")
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }

    responses = []
    errors = []

    def make_request(request_id: int) -> tuple[int, Optional[Dict], Optional[str]]:
        """Make a single request and return (id, response_body, error)."""
        try:
            response = requests.post(
                f"{BASE_URL}/api/forecast", json=payload, timeout=30
            )
            if response.status_code == 200:
                return (request_id, response.json(), None)
            else:
                return (
                    request_id,
                    None,
                    f"Status {response.status_code}: {response.text[:100]}",
                )
        except Exception as e:
            return (request_id, None, str(e))

    # Execute 10 concurrent requests
    num_requests = 10
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        for future in as_completed(futures):
            req_id, resp_body, error = future.result()
            if error:
                errors.append(f"Request {req_id}: {error}")
            else:
                responses.append((req_id, resp_body))

    if errors:
        result.record_error(0, f"Some requests failed: {errors}")
        return result

    if len(responses) != num_requests:
        result.record_error(
            0, f"Only {len(responses)}/{num_requests} requests succeeded"
        )
        return result

    # Verify state isolation: responses should be identical (same input)
    first_response = responses[0][1]
    structural_diffs = []
    numeric_diffs = []
    tolerance = 1e-10

    for req_id, resp in responses[1:]:
        # Check structure
        if set(resp.keys()) != set(first_response.keys()):
            structural_diffs.append(
                f"Request {req_id} has different keys: {set(resp.keys())} vs {set(first_response.keys())}"
            )

        # Check array lengths
        for key in ["history", "forecast"]:
            if key in first_response:
                if len(resp.get(key, [])) != len(first_response[key]):
                    structural_diffs.append(
                        f"Request {req_id} {key} length differs: {len(resp.get(key, []))} vs {len(first_response[key])}"
                    )

        # Check numeric values
        if "history" in first_response:
            for j, (first_item, resp_item) in enumerate(
                zip(first_response["history"], resp["history"])
            ):
                if "behavior_index" in first_item and "behavior_index" in resp_item:
                    diff = abs(
                        first_item["behavior_index"] - resp_item["behavior_index"]
                    )
                    if diff > tolerance:
                        numeric_diffs.append(
                            f"Request {req_id} history[{j}].behavior_index differs by {diff}"
                        )

    if structural_diffs:
        result.record_error(0, f"State leakage detected: {', '.join(structural_diffs)}")
        return result

    if numeric_diffs:
        result.add_validation_error(
            f"State leakage detected: {len(numeric_diffs)} numeric differences"
        )
        result.record_success(
            200,
            {
                "concurrent_requests": num_requests,
                "all_succeeded": True,
                "state_isolation": "violated" if numeric_diffs else "verified",
                "numeric_diffs": len(numeric_diffs),
            },
        )
    else:
        result.record_success(
            200,
            {
                "concurrent_requests": num_requests,
                "all_succeeded": True,
                "state_isolation": "verified",
                "responses_identical": True,
            },
        )

    return result


def validate_temporal_integrity() -> ValidationResult:
    """Validate temporal integrity by testing same request across different time contexts."""
    result = ValidationResult("/api/forecast (temporal)", "POST")

    # Test with different days_back values (simulating different time windows)
    test_cases = [
        {"days_back": 7, "forecast_horizon": 7, "name": "min_window"},
        {"days_back": 30, "forecast_horizon": 7, "name": "standard_window"},
        {"days_back": 90, "forecast_horizon": 7, "name": "extended_window"},
    ]

    responses = []
    errors = []

    base_payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
    }

    for test_case in test_cases:
        payload = {**base_payload, **test_case}
        try:
            response = requests.post(
                f"{BASE_URL}/api/forecast", json=payload, timeout=30
            )
            if response.status_code == 200:
                responses.append((test_case["name"], response.json()))
            else:
                errors.append(
                    f"{test_case['name']}: Status {response.status_code}: {response.text[:100]}"
                )
        except Exception as e:
            errors.append(f"{test_case['name']}: {str(e)}")

    if errors:
        result.record_error(0, f"Some temporal tests failed: {errors}")
        return result

    if len(responses) != len(test_cases):
        result.record_error(
            0, f"Only {len(responses)}/{len(test_cases)} temporal tests succeeded"
        )
        return result

    # Verify temporal consistency:
    # 1. Each response should have history length matching days_back
    # 2. Forecasts should be consistent (same horizon)
    # 3. No future data should leak into past windows

    temporal_issues = []

    for name, resp in responses:
        # Verify history length is at least days_back (system may return more if data available)
        test_case = next(tc for tc in test_cases if tc["name"] == name)
        expected_min_history_length = test_case["days_back"]
        actual_history_length = len(resp.get("history", []))

        if actual_history_length < expected_min_history_length:
            temporal_issues.append(
                f"{name}: History length insufficient: expected at least {expected_min_history_length}, got {actual_history_length}"
            )

        # Verify forecast horizon is consistent
        expected_forecast_length = test_case["forecast_horizon"]
        actual_forecast_length = len(resp.get("forecast", []))

        if actual_forecast_length != expected_forecast_length:
            temporal_issues.append(
                f"{name}: Forecast length mismatch: expected {expected_forecast_length}, got {actual_forecast_length}"
            )

        # Verify timestamps are in correct order (past to future)
        if "history" in resp and len(resp["history"]) > 1:
            timestamps = [item.get("timestamp") for item in resp["history"]]
            if timestamps != sorted(timestamps):
                temporal_issues.append(
                    f"{name}: History timestamps not in chronological order"
                )

        if "forecast" in resp and len(resp["forecast"]) > 1:
            timestamps = [item.get("timestamp") for item in resp["forecast"]]
            if timestamps != sorted(timestamps):
                temporal_issues.append(
                    f"{name}: Forecast timestamps not in chronological order"
                )

    # Verify no future leakage: shorter window should not have data beyond its range
    # Compare overlapping periods between windows
    min_window_resp = next(r[1] for r in responses if r[0] == "min_window")
    standard_window_resp = next(r[1] for r in responses if r[0] == "standard_window")

    if "history" in min_window_resp and "history" in standard_window_resp:
        min_timestamps = {item.get("timestamp") for item in min_window_resp["history"]}
        standard_timestamps = {
            item.get("timestamp") for item in standard_window_resp["history"]
        }

        # All timestamps in min_window should be in standard_window
        if not min_timestamps.issubset(standard_timestamps):
            temporal_issues.append(
                "Future leakage: min_window contains timestamps not in standard_window"
            )

    if temporal_issues:
        result.add_validation_error(
            f"Temporal integrity violations: {len(temporal_issues)} issues"
        )
        # Store issues in response_body for debugging
        result.record_success(
            200,
            {
                "temporal_tests": len(test_cases),
                "temporal_integrity": "violated",
                "issues": temporal_issues,
                "all_issues": temporal_issues,  # Duplicate for visibility
            },
        )
    else:
        result.record_success(
            200,
            {
                "temporal_tests": len(test_cases),
                "temporal_integrity": "verified",
                "no_future_leakage": True,
                "chronological_order": True,
            },
        )

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

    # Determinism tests
    print("\n14. Validating determinism (5 identical requests)...")
    results.append(validate_determinism())

    # Contract permanence tests
    print("\n15. Validating contract permanence...")
    results.append(validate_contract_permanence())

    # State isolation and concurrency tests
    print("\n16. Validating state isolation (concurrent requests)...")
    results.append(validate_state_isolation_concurrent())

    # Temporal integrity tests
    print("\n17. Validating temporal integrity...")
    results.append(validate_temporal_integrity())

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
