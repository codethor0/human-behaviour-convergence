#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Generate dependency lock files with hashes for reproducible builds

set -euo pipefail

echo "=== Generating Dependency Lock Files ==="

# Python dependencies with hashes
echo "Generating requirements-lock.txt with hashes..."
pip-compile --generate-hashes --output-file=requirements-lock.txt requirements.txt || {
    echo "pip-compile not available, using pip hash generation..."
    pip hash requirements.txt > requirements-lock.txt || {
        echo "WARNING: Could not generate hashes for requirements.txt"
    }
}

# Development dependencies with hashes
if [ -f requirements-dev.txt ]; then
    echo "Generating requirements-dev-lock.txt with hashes..."
    pip-compile --generate-hashes --output-file=requirements-dev-lock.txt requirements-dev.txt || {
        echo "WARNING: Could not generate hashes for requirements-dev.txt"
    }
fi

# Backend dependencies with hashes
if [ -f app/backend/requirements.txt ]; then
    echo "Generating app/backend/requirements-lock.txt with hashes..."
    pip-compile --generate-hashes --output-file=app/backend/requirements-lock.txt app/backend/requirements.txt || {
        echo "WARNING: Could not generate hashes for app/backend/requirements.txt"
    }
fi

# Node.js dependencies (package-lock.json should already exist)
if [ -f app/frontend/package.json ]; then
    echo "Verifying package-lock.json exists..."
    if [ ! -f app/frontend/package-lock.json ]; then
        echo "Generating package-lock.json..."
        cd app/frontend && npm install --package-lock-only && cd ../..
    else
        echo "package-lock.json exists"
    fi
fi

echo "=== Dependency Lock Generation Complete ==="
