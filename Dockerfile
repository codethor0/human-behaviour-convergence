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

RUN pip install --upgrade pip \
    && pip install .

FROM python:3.10-slim AS runtime

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
