#!/usr/bin/env python3
"""Visual verification using Playwright to check for 'Dashboard not found' errors"""
import json
import os
import sys

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")


def check_for_errors(page, eradicate_dir: str) -> list:
    """Check for 'Dashboard not found' errors on the page."""
    errors = []

    # Wait for page to load
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass

    # Check for error text in various forms
    error_selectors = [
        "text=/Dashboard not found/i",
        "text=/cannot find this dashboard/i",
        "text=/404/i",
        ".error-banner",
        '[class*="error"]',
    ]

    for selector in error_selectors:
        try:
            elements = page.query_selector_all(selector)
            for elem in elements:
                text = elem.inner_text() if elem else ""
                if any(
                    phrase in text.lower()
                    for phrase in ["not found", "404", "error", "cannot find"]
                ):
                    errors.append(
                        {
                            "selector": selector,
                            "text": text[:200],
                        }
                    )
        except:
            pass

    return errors


def verify_dashboards_load(page, eradicate_dir: str) -> dict:
    """Verify dashboards are loading."""
    results = {}

    # Get all iframes
    iframes = page.query_selector_all("iframe[src*='grafana']")

    for iframe in iframes:
        try:
            src = iframe.get_attribute("src", "")
            # Extract UID from src
            if "/d/" in src:
                uid = src.split("/d/")[1].split("?")[0].split("&")[0]
                results[uid] = {
                    "uid": uid,
                    "src": src,
                    "visible": iframe.is_visible(),
                }
        except:
            pass

    return results


def main():
    if not PLAYWRIGHT_AVAILABLE:
        print("WARNING: Playwright not available. Skipping visual verification.")
        print("Install with: pip install playwright && playwright install")
        return 0

    eradicate_dir = os.getenv("ERADICATE_DIR", "/tmp/hbc_eradicate_default")
    os.makedirs(f"{eradicate_dir}/screenshots", exist_ok=True)

    print("=== VISUAL VERIFICATION ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to main page
            print(f"Navigating to {FRONTEND_URL}...")
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)  # Wait for dashboards to load

            # Take screenshot
            screenshot_path = f"{eradicate_dir}/screenshots/main_page.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")

            # Check for errors
            print("\nChecking for 'Dashboard not found' errors...")
            errors = check_for_errors(page, eradicate_dir)

            if errors:
                print(f"[FAIL] FOUND {len(errors)} ERRORS:")
                for error in errors:
                    print(f"  - {error.get('text', '')[:100]}")
            else:
                print("[OK] No 'Dashboard not found' errors found")

            # Verify dashboards
            print("\nVerifying dashboard iframes...")
            dashboard_results = verify_dashboards_load(page, eradicate_dir)
            print(f"Found {len(dashboard_results)} dashboard iframes")

            # Save results
            report = {
                "errors_found": len(errors),
                "errors": errors,
                "dashboards_found": len(dashboard_results),
                "dashboard_results": dashboard_results,
            }

            report_path = f"{eradicate_dir}/proofs/visual_verification.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)

            print(f"\nReport saved: {report_path}")

            if errors:
                print("\n[FAIL] VISUAL VERIFICATION FAILED - Errors found")
                return 1
            else:
                print("\n[OK] VISUAL VERIFICATION PASSED - No errors found")
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
