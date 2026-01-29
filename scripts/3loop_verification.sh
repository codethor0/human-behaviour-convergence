#!/bin/bash
# 3-Loop Clean Verification for Dashboard Eradication Protocol

set -e

ERADICATE_DIR="${ERADICATE_DIR:-/tmp/hbc_eradicate_default}"
LOOPS=3

echo "=== 3-LOOP CLEAN VERIFICATION ==="
echo "Eradicate Dir: $ERADICATE_DIR"
echo "Loops: $LOOPS"
echo ""

mkdir -p "$ERADICATE_DIR"/proofs

for loop in $(seq 1 $LOOPS); do
    echo "=========================================="
    echo "=== RESURRECTION LOOP $loop ==="
    echo "=========================================="

    LOOP_DIR="$ERADICATE_DIR/loop_${loop}"
    mkdir -p "$LOOP_DIR"

    # Restart stack
    echo "Restarting stack..."
    cd /Users/thor/Projects/human-behaviour-convergence
    docker compose down -v 2>/dev/null || true
    docker compose up -d --build
    echo "Waiting for services to start..."
    sleep 30

    # Run triage
    echo "Running triage..."
    export ERADICATE_DIR="$LOOP_DIR"
    python3 scripts/full_dashboard_triage.py > "$LOOP_DIR/triage_output.txt" 2>&1
    TRIAGE_EXIT=$?

    # Check results
    if [ $TRIAGE_EXIT -eq 0 ]; then
        DEAD_COUNT=$(grep -c "DEAD" "$LOOP_DIR/triage_output.txt" 2>/dev/null || echo "0")

        if [ "$DEAD_COUNT" -eq 0 ]; then
            echo "✅ LOOP $loop PASSED - No dead dashboards"
            echo "PASSED" > "$LOOP_DIR/status.txt"
        else
            echo "❌ LOOP $loop FAILED - $DEAD_COUNT dead dashboards found"
            echo "FAILED" > "$LOOP_DIR/status.txt"
            exit 1
        fi
    else
        echo "❌ LOOP $loop FAILED - Triage script error"
        echo "FAILED" > "$LOOP_DIR/status.txt"
        exit 1
    fi

    # Visual verification (if Playwright available)
    echo "Running visual verification..."
    python3 scripts/visual_verification_playwright.py > "$LOOP_DIR/visual_output.txt" 2>&1 || true

    echo ""
done

echo "=========================================="
echo "=== ALL LOOPS COMPLETED ==="
echo "=========================================="

# Generate final report
cat > "$ERADICATE_DIR/proofs/3loop_certification.txt" << EOF
3-LOOP CLEAN VERIFICATION CERTIFICATE
=====================================
Date: $(date +%Y-%m-%d\ %H:%M:%S)

All $LOOPS loops completed successfully.

Loop Results:
EOF

for loop in $(seq 1 $LOOPS); do
    LOOP_DIR="$ERADICATE_DIR/loop_${loop}"
    if [ -f "$LOOP_DIR/status.txt" ]; then
        STATUS=$(cat "$LOOP_DIR/status.txt")
        echo "Loop $loop: $STATUS" >> "$ERADICATE_DIR/proofs/3loop_certification.txt"
    else
        echo "Loop $loop: UNKNOWN" >> "$ERADICATE_DIR/proofs/3loop_certification.txt"
    fi
done

cat "$ERADICATE_DIR/proofs/3loop_certification.txt"
echo ""
echo "✅ 3-LOOP VERIFICATION COMPLETE"
