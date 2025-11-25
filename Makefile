# SPDX-License-Identifier: MIT-0
.PHONY: dev test lint format clean install

# Start development environment
dev:
	docker compose up --build

# Run tests in Docker
test:
	docker compose run --rm test

# Run linting
lint:
	ruff check app/ tests/ scripts/ --exclude="notebooks|\.venv|\.git"

# Format code
format:
	black app/ tests/ scripts/

# Install dependencies locally
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -r app/backend/requirements.txt
	pip install -e .

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
