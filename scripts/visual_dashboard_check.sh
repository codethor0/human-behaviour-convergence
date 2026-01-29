#!/bin/bash
# Visual Dashboard Verification - Check for "Dashboard not found" errors

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3100}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
ERADICATE_DIR="/tmp/hbc_eradicate_visual_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ERADICATE_DIR"/{screenshots,proofs}

echo "=== VISUAL DASHBOARD VERIFICATION ==="
echo "Frontend URL: $FRONTEND_URL"
echo "Grafana URL: $GRAFANA_URL"
echo ""

# Fetch the main page HTML
echo "Fetching main page..."
curl -s "$FRONTEND_URL" > "$ERADICATE_DIR/proofs/main_page.html"

# Check for "Dashboard not found" text
echo "Checking for 'Dashboard not found' errors..."
ERROR_COUNT=$(grep -i "dashboard not found\|cannot find this dashboard\|404" "$ERADICATE_DIR/proofs/main_page.html" | wc -l | tr -d ' ')

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "❌ FOUND $ERROR_COUNT potential error messages"
    grep -i "dashboard not found\|cannot find this dashboard\|404" "$ERADICATE_DIR/proofs/main_page.html" > "$ERADICATE_DIR/proofs/errors_found.txt"
    cat "$ERADICATE_DIR/proofs/errors_found.txt"
else
    echo "✅ No 'Dashboard not found' errors in HTML"
fi

# Extract all dashboard UIDs from the page
echo ""
echo "Extracting dashboard UIDs from page..."
grep -oE 'data-testid="dashboard-embed-[^"]+"' "$ERADICATE_DIR/proofs/main_page.html" | \
    sed 's/data-testid="dashboard-embed-//' | sed 's/"//' | sort -u > "$ERADICATE_DIR/proofs/dashboard_uids_in_page.txt"

DASHBOARD_COUNT=$(wc -l < "$ERADICATE_DIR/proofs/dashboard_uids_in_page.txt" | tr -d ' ')
echo "Found $DASHBOARD_COUNT dashboard embeds in page"

# Extract iframe sources
echo ""
echo "Checking iframe sources..."
grep -oE 'src="[^"]*grafana[^"]*"' "$ERADICATE_DIR/proofs/main_page.html" | \
    grep -oE '/d/[^?&"]+' | sed 's|/d/||' | sort -u > "$ERADICATE_DIR/proofs/iframe_uids.txt"

IFRAME_COUNT=$(wc -l < "$ERADICATE_DIR/proofs/iframe_uids.txt" | tr -d ' ')
echo "Found $IFRAME_COUNT iframe sources pointing to Grafana"

# Verify each dashboard exists in Grafana
echo ""
echo "Verifying dashboards exist in Grafana..."
DEAD_COUNT=0
while IFS= read -r uid; do
    if [ -n "$uid" ]; then
        response=$(curl -s "$GRAFANA_URL/api/dashboards/uid/$uid" 2>/dev/null)
        if echo "$response" | grep -q '"message":"Dashboard not found"'; then
            echo "  ❌ $uid - NOT FOUND"
            echo "$uid" >> "$ERADICATE_DIR/proofs/dead_dashboards.txt"
            DEAD_COUNT=$((DEAD_COUNT + 1))
        else
            echo "  ✅ $uid - exists"
        fi
    fi
done < "$ERADICATE_DIR/proofs/dashboard_uids_in_page.txt"

# Summary
echo ""
echo "=== SUMMARY ==="
echo "Dashboards in page: $DASHBOARD_COUNT"
echo "Iframes found: $IFRAME_COUNT"
echo "Dead dashboards: $DEAD_COUNT"
echo "Error messages: $ERROR_COUNT"

if [ "$DEAD_COUNT" -eq 0 ] && [ "$ERROR_COUNT" -eq 0 ]; then
    echo ""
    echo "✅ VERIFICATION PASSED - All dashboards loading correctly"
    exit 0
else
    echo ""
    echo "❌ VERIFICATION FAILED - Issues found"
    exit 1
fi
