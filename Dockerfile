FROM python:3.10-slim AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY hbc ./hbc
COPY app ./app
COPY requirements.txt requirements-dev.txt ./
COPY app/backend/requirements.txt ./app/backend/

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -r requirements-dev.txt \
    && pip install -r app/backend/requirements.txt \
    && pip install .

FROM python:3.10-slim AS runtime

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
