# Deployment Guide

This document outlines how to deploy the Behavior Convergence Explorer application to production environments.

## Architecture Overview

The application consists of two main components:

1. **Backend (FastAPI)**: Python-based API server for forecasting
2. **Frontend (Next.js)**: React-based web interface

## Prerequisites

- Python 3.10+ with pip
- Node.js 20+ with npm
- Environment variables configured (see below)

## Backend Deployment

### Option 1: Render / Heroku / Railway

1. **Create a Procfile:**
   ```
   web: uvicorn app.backend.app.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Set environment variables:**
   ```
   HOST=0.0.0.0
   PORT=8000
   ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
   CACHE_MAX_SIZE=100
   CACHE_TTL_MINUTES=5
   LOG_FORMAT=json
   LOG_LEVEL=INFO
   ```

3. **Deploy:**
   - Connect your repository to the platform
   - Configure build command: `pip install -r requirements.txt && pip install -r app/backend/requirements.txt`
   - Set start command: `uvicorn app.backend.app.main:app --host 0.0.0.0 --port $PORT`

### Option 2: Docker

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.10-slim

   WORKDIR /app

   COPY requirements.txt .
   COPY app/backend/requirements.txt ./app/backend/
   RUN pip install --no-cache-dir -r requirements.txt && \
       pip install --no-cache-dir -r app/backend/requirements.txt

   COPY . .

   EXPOSE 8000

   CMD ["uvicorn", "app.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and run:**
   ```bash
   docker build -t behavior-convergence-api .
   docker run -p 8000:8000 -e ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app behavior-convergence-api
   ```

## Frontend Deployment

### Vercel (Recommended)

1. **Configure project:**
   - Set framework preset to "Next.js"
   - Set root directory to `app/frontend`
   - Set build command: `npm run build`
   - Set output directory: `.next`

2. **Set environment variables:**
   ```
   NEXT_PUBLIC_API_BASE=https://your-backend-api.render.app
   ```

3. **Deploy:**
   ```bash
   npm install -g vercel
   cd app/frontend
   vercel
   ```

### Alternative: Static Export

1. **Update next.config.mjs:**
   ```javascript
   output: 'export',
   trailingSlash: true,
   ```

2. **Build and deploy:**
   ```bash
   cd app/frontend
   npm run build
   # Deploy the 'out' directory to any static hosting service
   ```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `127.0.0.1` |
| `PORT` | Server port | `8000` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |
| `CACHE_MAX_SIZE` | Maximum cache entries | `100` |
| `CACHE_TTL_MINUTES` | Cache TTL in minutes | `5` |
| `LOG_FORMAT` | Log format (text/json) | `text` |
| `LOG_LEVEL` | Log level | `INFO` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE` | Backend API URL | `http://localhost:8000` |

## Health Checks

The backend provides health check endpoints:

- `GET /health` - Simple liveness check
- `GET /api/forecasting/status` - Detailed system status
- `GET /api/cache/status` - Cache statistics

Configure your deployment platform to use `/health` for health checks.

## Monitoring

### Recommended Metrics

1. **API Metrics:**
   - Request rate and latency
   - Error rates (4xx, 5xx)
   - Cache hit/miss ratios (`/api/cache/status`)

2. **Data Source Health:**
   - Monitor `/api/forecasting/status` for data source availability
   - Track API response times for external data sources

3. **Forecasting Performance:**
   - Forecast generation latency
   - Model accuracy (when historical tracking is implemented)

### Logging

The backend supports structured JSON logging when `LOG_FORMAT=json`. Configure log aggregation (e.g., Datadog, Logtail) to collect and analyze logs.

## Scaling Considerations

1. **Backend:**
   - Use horizontal scaling with multiple API instances
   - Implement rate limiting for production (e.g., SlowAPI)
   - Use Redis for shared cache across instances

2. **Frontend:**
   - Next.js static export for maximum performance
   - CDN caching for static assets
   - Consider ISR (Incremental Static Regeneration) for forecast pages

## Security Checklist

- [ ] Set `ALLOWED_ORIGINS` to production frontend domain only
- [ ] Enable HTTPS for both backend and frontend
- [ ] Configure CORS properly
- [ ] Set secure HTTP headers (via FastAPI middleware)
- [ ] Rate limit API endpoints
- [ ] Keep dependencies updated (`pip-audit`, `npm audit`)
- [ ] Use secrets management for API keys (if added in future)

## Troubleshooting

### Backend won't start

- Check Python version: `python --version` (should be 3.10+)
- Verify dependencies: `pip install -r requirements.txt`
- Check logs for import errors
- Ensure PORT environment variable is set

### Frontend can't connect to backend

- Verify `NEXT_PUBLIC_API_BASE` is set correctly
- Check CORS settings: `ALLOWED_ORIGINS` must include frontend URL
- Test backend health: `curl https://your-backend-url/health`

### Forecast requests timeout

- Check external API connectivity (economic/weather data sources)
- Increase timeout values in data connectors
- Monitor cache hit rates (high miss rate may indicate issues)

## Support

For deployment issues, see:
- Backend API docs: `http://your-backend-url/docs` (Swagger UI)
- [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup
- [SECURITY.md](./SECURITY.md) for security concerns
