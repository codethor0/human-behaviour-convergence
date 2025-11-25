# Running with Docker

This guide explains how to run the Behavior Convergence application using Docker for local development and testing.

## Prerequisites

- Docker and Docker Compose installed
- Git repository cloned

## Quick Start

### Start Backend and Frontend

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up -d
```

This will start:
- **Backend API** on http://localhost:8000
- **Frontend UI** on http://localhost:3000

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Stop Services

```bash
docker compose down
```

## Services

### Backend

The backend service runs the FastAPI application.

**Environment Variables:**
- `CACHE_MAX_SIZE`: Maximum cache size (default: 100)
- `CACHE_TTL_MINUTES`: Cache TTL in minutes (default: 5)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)
- `MOBILITY_API_ENDPOINT`: Optional mobility API endpoint
- `MOBILITY_API_KEY`: Optional mobility API key
- `PUBLIC_HEALTH_API_ENDPOINT`: Optional public health API endpoint
- `PUBLIC_HEALTH_API_KEY`: Optional public health API key
- `SEARCH_TRENDS_API_ENDPOINT`: Optional search trends API endpoint
- `SEARCH_TRENDS_API_KEY`: Optional search trends API key

### Frontend

The frontend service runs the Next.js development server.

**Environment Variables:**
- `NEXT_PUBLIC_API_BASE`: Backend API base URL (default: http://localhost:8000)

### Test Service

Run automated tests:

```bash
docker compose run test
```

This runs pytest with coverage reporting.

## Running Tests

### Automated Regression Tests

```bash
# Run all tests
docker compose run test

# Or run tests locally (requires local Python environment)
pytest tests/ --cov --cov-report=term-missing -v
```

### Exploratory Testing

Run the live forecast demo script:

```bash
# Inside Docker
docker compose run backend python scripts/run_live_forecast_demo.py

# Locally (requires local Python environment)
python scripts/run_live_forecast_demo.py
```

The demo script will use configured data sources. Optional sources require environment variables to be set.

## Configuration

### Optional Data Sources

To enable optional data sources, set environment variables before starting:

```bash
export MOBILITY_API_ENDPOINT="https://api.example.com/mobility"
export MOBILITY_API_KEY="your-api-key"
export PUBLIC_HEALTH_API_ENDPOINT="https://api.example.com/health"
export PUBLIC_HEALTH_API_KEY="your-api-key"
export SEARCH_TRENDS_API_ENDPOINT="https://api.example.com/search"
export SEARCH_TRENDS_API_KEY="your-api-key"

docker compose up
```

Or create a `.env` file (not tracked in git):

```bash
MOBILITY_API_ENDPOINT=https://api.example.com/mobility
MOBILITY_API_KEY=your-api-key
PUBLIC_HEALTH_API_ENDPOINT=https://api.example.com/health
PUBLIC_HEALTH_API_KEY=your-api-key
SEARCH_TRENDS_API_ENDPOINT=https://api.example.com/search
SEARCH_TRENDS_API_KEY=your-api-key
```

Then run:

```bash
docker compose --env-file .env up
```

## Development

### Hot Reload

Both backend and frontend support hot reload when volumes are mounted (default configuration).

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuilding

```bash
# Rebuild all services
docker compose build

# Rebuild specific service
docker compose build backend
docker compose build frontend
```

## Troubleshooting

### Port Already in Use

If ports 8000 or 3000 are already in use, modify `docker-compose.yml` to use different ports:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change host port
  frontend:
    ports:
      - "3001:3000"  # Change host port
```

### Frontend Cannot Connect to Backend

Ensure `NEXT_PUBLIC_API_BASE` in frontend service points to the correct backend URL. In Docker, use `http://backend:8000` for internal communication, or `http://localhost:8000` if accessing from browser.

### Health Check Fails

The backend health check uses curl. If it fails, check backend logs:

```bash
docker compose logs backend
```

## Production Considerations

This Docker setup is optimized for local development. For production:

- Use production builds (not dev mode)
- Set appropriate environment variables
- Use proper secrets management
- Configure reverse proxy (nginx, etc.)
- Enable HTTPS
- Set up monitoring and logging
