# Environment Variables

This document describes all environment variables used by the Human Behaviour Convergence application.

## Backend API Configuration

### `HOST`
- **Default:** `127.0.0.1`
- **Description:** Host address for the FastAPI server
- **Usage:** `app/backend/app/main.py`

### `PORT`
- **Default:** `8000`
- **Description:** Port number for the FastAPI server
- **Usage:** `app/backend/app/main.py`

### `APP_VERSION`
- **Default:** `0.1.0` (from FastAPI app.version)
- **Description:** Application version string
- **Usage:** `/api/status` endpoint

### `GIT_COMMIT`
- **Default:** `None`
- **Description:** Git commit hash for version tracking
- **Usage:** `/api/status` endpoint

## CORS Configuration

### `ALLOWED_ORIGINS`
- **Default:** `http://localhost:3000,http://127.0.0.1:3000`
- **Description:** Comma-separated list of allowed CORS origins
- **Usage:** FastAPI CORS middleware configuration
- **Example:** `http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100`

## Cache Configuration

### `CACHE_MAX_SIZE`
- **Default:** `100`
- **Description:** Maximum number of cache entries
- **Usage:** CSV response caching in `app/backend/app/main.py`

### `CACHE_TTL_MINUTES`
- **Default:** `5`
- **Description:** Time-to-live for cache entries in minutes
- **Usage:** CSV response caching in `app/backend/app/main.py`

### `CACHE_DEBUG`
- **Default:** `0` (disabled)
- **Description:** Enable debug logging for cache operations (set to `1` to enable)
- **Usage:** Cache debugging in `app/backend/app/main.py`

## Logging Configuration

### `LOG_FORMAT`
- **Default:** `text`
- **Description:** Log output format (`text` or `json`)
- **Usage:** Structlog configuration in `app/backend/app/main.py`

### `LOG_LEVEL`
- **Default:** `INFO`
- **Description:** Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Usage:** Docker compose configuration

## Database Configuration

### `HBC_DB_PATH`
- **Default:** `data/hbc.db` (relative to project root)
- **Description:** Path to SQLite database file for forecast storage
- **Usage:** `app/storage/db.py`

## Frontend Configuration

### `NEXT_PUBLIC_API_BASE`
- **Default:** `http://localhost:8100`
- **Description:** Base URL for the backend API
- **Usage:** Next.js frontend API calls
- **Note:** Must be prefixed with `NEXT_PUBLIC_` to be accessible in browser

## Optional Data Source API Keys

These environment variables are optional. The system will function without them, but with limited data sources.

### FRED Economic Data

#### `FRED_API_KEY`
- **Default:** `None`
- **Description:** API key for Federal Reserve Economic Data (FRED)
- **Required:** No (system works without it)
- **Get key:** https://fred.stlouisfed.org/docs/api/api_key.html
- **Usage:** `app/services/ingestion/economic_fred.py`

### Mobility Data Source

#### `MOBILITY_API_ENDPOINT`
- **Default:** `""` (empty string)
- **Description:** API endpoint URL for mobility data
- **Required:** No

#### `MOBILITY_API_KEY`
- **Default:** `""` (empty string)
- **Description:** API key for mobility data source
- **Required:** No
- **Usage:** `app/services/ingestion/mobility.py`

### Public Health Data Source

#### `PUBLIC_HEALTH_API_ENDPOINT`
- **Default:** `""` (empty string)
- **Description:** API endpoint URL for public health data
- **Required:** No

#### `PUBLIC_HEALTH_API_KEY`
- **Default:** `""` (empty string)
- **Description:** API key for public health data source
- **Required:** No
- **Usage:** `app/services/ingestion/public_health.py`

### Search Trends Data Source

#### `SEARCH_TRENDS_API_ENDPOINT`
- **Default:** `""` (empty string)
- **Description:** API endpoint URL for search trends data
- **Required:** No

#### `SEARCH_TRENDS_API_KEY`
- **Default:** `""` (empty string)
- **Description:** API key for search trends data source
- **Required:** No
- **Usage:** `app/services/ingestion/search_trends.py`

### OpenStates Legislative Activity

#### `OPENSTATES_API_KEY`
- **Default:** `""` (empty string)
- **Description:** API key for OpenStates legislative activity data
- **Required:** Yes (for legislative_activity source)
- **Get key:** https://openstates.org/api/register/
- **Usage:** `app/services/ingestion/openstates_legislative.py`

### NASA FIRMS Active Fires

#### `FIRMS_MAP_KEY`
- **Default:** `""` (empty string)
- **Description:** API key for NASA FIRMS active fire data
- **Required:** No (uses mock data if not set)
- **Get key:** https://firms.modaps.eosdis.nasa.gov/api/
- **Usage:** `connectors/firms_fires.py`

## Example .env File

Create a `.env` file in the project root with the following structure:

```bash
# Backend API Configuration
HOST=127.0.0.1
PORT=8000
APP_VERSION=0.1.0
GIT_COMMIT=

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100,http://127.0.0.1:3100

# Cache Configuration
CACHE_MAX_SIZE=100
CACHE_TTL_MINUTES=5
CACHE_DEBUG=0

# Logging Configuration
LOG_FORMAT=text
LOG_LEVEL=INFO

# Database Configuration
HBC_DB_PATH=data/hbc.db

# Frontend Configuration
NEXT_PUBLIC_API_BASE=http://localhost:8100

# Data Source API Keys
# OpenStates Legislative Activity (Required for legislative_activity source)
OPENSTATES_API_KEY=

# FRED Economic Data (Optional)
FRED_API_KEY=

# NASA FIRMS Active Fires (Optional)
FIRMS_MAP_KEY=

# Mobility Data (Optional)
MOBILITY_API_ENDPOINT=
MOBILITY_API_KEY=

# Public Health Data (Optional)
PUBLIC_HEALTH_API_ENDPOINT=
PUBLIC_HEALTH_API_KEY=

# Search Trends Data (Optional)
SEARCH_TRENDS_API_ENDPOINT=
SEARCH_TRENDS_API_KEY=
```

## Notes

- All environment variables have sensible defaults and the application will run without any configuration
- Optional API keys can be added incrementally as data sources are integrated
- The `.env` file is gitignored for security (see `.gitignore`)
- Docker Compose sets some environment variables automatically (see `docker-compose.yml`)
