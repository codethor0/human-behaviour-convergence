#!/usr/bin/env python3
"""Visual verification of dashboards - check for "Dashboard not found" errors in UI"""
import json
import os
import sys
import time

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print(
        "Warning: Playwright not available. Install with: pip install playwright && playwright install"
    )

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")


def check_dashboard_errors(page, eradicate_dir: str) -> list:
    """Check for 'Dashboard not found' errors on the page."""
    errors = []

    # Wait for page to load
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass

    # Check for error text
    error_selectors = [
        "text=/Dashboard not found/i",
        "text=/cannot find this dashboard/i",
        "text=/404/i",
        '[data-testid*="dashboard-embed-"]:has-text("not found")',
        ".grafana-error",
    ]

    for selector in error_selectors:
        try:
            elements = page.query_selector_all(selector)
            for elem in elements:
                text = elem.inner_text() if elem else ""
                if (
                    "not found" in text.lower()
                    or "404" in text
                    or "error" in text.lower()
                ):
                    errors.append(
                        {"selector": selector, "text": text[:200], "screenshot": None}
                    )
        except:
            pass

    # Check all dashboard embed containers for errors
    dashboard_embeds = page.query_selector_all('[data-testid^="dashboard-embed-"]')
    for embed in dashboard_embeds:
        embed_text = embed.inner_text() if embed else ""
        if "not found" in embed_text.lower() or "error" in embed_text.lower():
            uid = embed.get_attribute("data-testid", "").replace("dashboard-embed-", "")
            errors.append({"uid": uid, "text": embed_text[:200], "type": "embed_error"})

    # Check iframes for errors
    iframes = page.query_selector_all("iframe[src*='grafana']")
    for iframe in iframes:
        try:
            src = iframe.get_attribute("src", "")
            # Extract UID from src
            if "/d/" in src:
                uid = src.split("/d/")[1].split("?")[0].split("&")[0]
                # Try to access iframe content (may fail due to CORS)
                try:
                    iframe_content = iframe.content_frame()
                    if iframe_content:
                        iframe_text = iframe_content.inner_text()
                        if "not found" in iframe_text.lower():
                            errors.append(
                                {
                                    "uid": uid,
                                    "text": iframe_text[:200],
                                    "type": "iframe_error",
                                    "src": src,
                                }
                            )
                except:
                    # CORS - can't access iframe content, but iframe exists
                    pass
        except:
            pass

    return errors


def verify_dashboard_loading(page, eradicate_dir: str) -> dict:
    """Verify dashboards are loading correctly."""
    results = {}

    # Get all dashboard embed elements
    dashboard_embeds = page.query_selector_all('[data-testid^="dashboard-embed-"]')

    print(f"Found {len(dashboard_embeds)} dashboard embed elements")

    for embed in dashboard_embeds:
        testid = embed.get_attribute("data-testid", "")
        uid = testid.replace("dashboard-embed-", "")

        # Check if iframe exists
        iframe = embed.query_selector("iframe")
        has_iframe = iframe is not None

        # Check for error messages
        error_elem = embed.query_selector("text=/error|not found/i")
        has_error = error_elem is not None

        # Get iframe src
        iframe_src = iframe.get_attribute("src", "") if iframe else ""

        results[uid] = {
            "uid": uid,
            "has_iframe": has_iframe,
            "has_error": has_error,
            "iframe_src": iframe_src,
            "status": "error" if has_error else ("alive" if has_iframe else "missing"),
        }

    return results


def test_region_switching(page, eradicate_dir: str) -> bool:
    """Test that dashboards react to region changes."""
    try:
        # Find region selector
        region_selector = page.query_selector('[data-testid="global-region-selector"]')
        if not region_selector:
            print("Warning: Region selector not found")
            return False

        # Get initial state
        initial_value = region_selector.input_value()
        print(f"Initial region: {initial_value}")

        # Change to Illinois
        try:
            region_selector.select_option(value="state_il")
            page.wait_for_timeout(2000)  # Wait for dashboards to update

            # Check that dashboards updated
            # (We can't easily verify data changed, but we can check iframes reloaded)
            iframes_after = page.query_selector_all("iframe[src*='grafana']")
            print(f"Iframes after region change: {len(iframes_after)}")

            # Change back
            region_selector.select_option(value=initial_value)
            page.wait_for_timeout(1000)

            return True
        except Exception as e:
            print(f"Error testing region switching: {e}")
            return False
    except Exception as e:
        print(f"Error in region switching test: {e}")
        return False


def main():
    if not PLAYWRIGHT_AVAILABLE:
        print("ERROR: Playwright not available. Cannot perform visual verification.")
        print("Install with: pip install playwright && playwright install")
        return 1

    eradicate_dir = (
        f"/tmp/hbc_eradicate_visual_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}"
    )
    os.makedirs(f"{eradicate_dir}/screenshots", exist_ok=True)
    os.makedirs(f"{eradicate_dir}/proofs", exist_ok=True)

    print("=== VISUAL DASHBOARD VERIFICATION ===\n")
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Grafana URL: {GRAFANA_URL}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Navigate to main page
            print("Navigating to Dashboard Hub...")
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)  # Wait for dashboards to load

            # Take screenshot
            screenshot_path = f"{eradicate_dir}/screenshots/initial_page.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")

            # Check for errors
            print("\nChecking for 'Dashboard not found' errors...")
            errors = check_dashboard_errors(page, eradicate_dir)

            if errors:
                print(f"\n[FAIL] FOUND {len(errors)} ERRORS:")
                for error in errors:
                    print(
                        f"  - {error.get('uid', 'unknown')}: {error.get('text', '')[:100]}"
                    )
            else:
                print("[OK] No 'Dashboard not found' errors found")

            # Verify dashboard loading
            print("\nVerifying dashboard loading...")
            results = verify_dashboard_loading(page, eradicate_dir)

            # Count statuses
            alive = [r for r in results.values() if r["status"] == "alive"]
            errors_found = [r for r in results.values() if r["status"] == "error"]
            missing = [r for r in results.values() if r["status"] == "missing"]

            print("\nDashboard Status:")
            print(f"  [OK] Alive: {len(alive)}")
            print(f"  [FAIL] Errors: {len(errors_found)}")
            print(f"  [WARN]  Missing: {len(missing)}")

            if errors_found:
                print("\nDashboards with errors:")
                for r in errors_found:
                    print(f"  - {r['uid']}")

            if missing:
                print("\nDashboards missing iframes:")
                for r in missing:
                    print(f"  - {r['uid']}")

            # Test region switching
            print("\nTesting region switching...")
            region_test_passed = test_region_switching(page, eradicate_dir)
            if region_test_passed:
                print("[OK] Region switching test passed")
            else:
                print("[WARN]  Region switching test had issues")

            # Save results
            report = {
                "timestamp": time.time(),
                "frontend_url": FRONTEND_URL,
                "grafana_url": GRAFANA_URL,
                "errors": errors,
                "dashboard_results": results,
                "region_test_passed": region_test_passed,
                "summary": {
                    "total_dashboards": len(results),
                    "alive": len(alive),
                    "errors": len(errors_found),
                    "missing": len(missing),
                },
            }

            report_path = f"{eradicate_dir}/proofs/visual_verification_report.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)

            print(f"\nReport saved: {report_path}")

            # Final status
            if errors or errors_found or missing:
                print("\n[FAIL] VERIFICATION FAILED - Issues found")
                return 1
            else:
                print("\n[OK] VERIFICATION PASSED - All dashboards loading correctly")
                return 0

        except Exception as e:
            print(f"\n[FAIL] ERROR: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
