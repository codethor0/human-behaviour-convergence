# --- Dockerfile for one-command onboarding ---
FROM python:3.10-slim

# Set up working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# Copy source code
COPY . .

# Expose default port
EXPOSE 8000

# Default command: run FastAPI app with Uvicorn
CMD ["uvicorn", "app.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
