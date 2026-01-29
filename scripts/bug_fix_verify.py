#!/usr/bin/env python3
"""Phase 4: Verify All Fixes"""
import json
import os
import sys
import requests
import time


def check_health_endpoint(url, expected_status=200, max_duration_ms=50):
    """Check health endpoint."""
    try:
        start = time.time()
        response = requests.get(url, timeout=2)
        duration_ms = (time.time() - start) * 1000

        if response.status_code == expected_status and duration_ms < max_duration_ms:
            return {
                "status": "pass",
                "duration_ms": duration_ms,
                "response": (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else response.text[:200]
                ),
            }
        else:
            return {
                "status": "fail",
                "reason": f"Status: {response.status_code}, Duration: {duration_ms}ms",
                "duration_ms": duration_ms,
            }
    except Exception as e:
        return {"status": "fail", "error": str(e)}


def main():
    fix_dir = os.getenv("FIX_DIR", "/tmp/hbc_fixes_default")
    os.makedirs(f"{fix_dir}/evidence", exist_ok=True)

    print("=== PHASE 4: VERIFICATION ===\n")

    results = {}

    # Check health endpoints
    print("Checking health endpoints...")
    health_checks = {
        "backend": ("http://localhost:8100/health", 200),
        "frontend": (
            "http://localhost:3100/health",
            200,
        ),  # Changed from /api/health to /health
        "grafana": ("http://localhost:3001/api/health", 200),
        "prometheus": ("http://localhost:9090/-/ready", 200),
    }

    for service, (url, expected_status) in health_checks.items():
        print(f"  {service}...", end=" ", flush=True)
        result = check_health_endpoint(url, expected_status)
        results[service] = result

        if result["status"] == "pass":
            print(f"[OK] HEALTHY ({result.get('duration_ms', 0):.1f}ms)")
        else:
            print(
                f"[FAIL] UNHEALTHY: {result.get('reason', result.get('error', 'Unknown'))}"
            )

    # Save results
    with open(f"{fix_dir}/evidence/health_matrix.json", "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    healthy_count = sum(1 for r in results.values() if r["status"] == "pass")
    total_count = len(results)

    print("\n=== SUMMARY ===")
    print(f"Healthy endpoints: {healthy_count}/{total_count}")

    if healthy_count == total_count:
        print("[OK] ALL HEALTH ENDPOINTS: OPERATIONAL")
        with open(f"{fix_dir}/evidence/VERIFICATION_PASS.txt", "w") as f:
            f.write("VERIFICATION PASSED\n")
            f.write(f"All {total_count} health endpoints operational\n")
        return 0
    else:
        print("[FAIL] SOME ENDPOINTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
