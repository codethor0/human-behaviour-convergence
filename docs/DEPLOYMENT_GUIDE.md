# Deployment Guide

**Purpose:** Guide for deploying the behavioral forecasting system across local, staging, and production environments

**Last Updated:** 2026-01-19

---

## Overview

This guide covers deploying the behavioral forecasting system in three environments:
- **Local Development:** Permissive settings, fast iteration, local Docker stack
- **Staging:** Production-like configuration, testing ground, tighter security
- **Production:** Locked-down settings, monitoring required, high availability

**Architecture:** All environments use the same Docker stack:
- Backend (FastAPI)
- Frontend (Next.js)
- Prometheus (metrics collection)
- Grafana (analytics dashboards)

---

## Table of Contents

1. [Local Development Deployment](#local-development-deployment)
2. [Staging Deployment](#staging-deployment)
3. [Production Deployment](#production-deployment)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Security Considerations](#security-considerations)
6. [Monitoring & Health Checks](#monitoring-health-checks)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Local Development Deployment

**Purpose:** Fast iteration, debugging, testing changes

### Prerequisites

- Docker and Docker Compose installed
- Git repository cloned
- Python 3.11+ (for local testing outside Docker)
- Node.js 18+ (for frontend development)

### Deployment Steps

1. **Clone Repository:**
   ```bash
   git clone https://github.com/your-org/human-behaviour-convergence.git
   cd human-behaviour-convergence
   ```

2. **No `.env` Required for Local:**
   - Local dev uses permissive defaults
   - All services accessible on `localhost`
   - CORS allows all origins

3. **Start Stack:**
   ```bash
   ./ops/dev_watch_docker.sh
   ```
   This script:
   - Builds Docker images
   - Starts all services
   - Waits for health checks
   - Performs CORS validation
   - Tails logs

4. **Verify Deployment:**
   ```bash
   ./ops/verify_gate_a.sh
   ./ops/verify_gate_grafana.sh
   ```
   Both should report GREEN.

5. **Access Services:**
   - Backend API: http://localhost:8100
   - Frontend: http://localhost:3100
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001 (admin/admin)
   - Operator Console: http://localhost:3100/ops

### Local Configuration

**CORS:** Permissive (allows all origins)
```python
# app/backend/app/main.py (dev default)
allow_origins=["*"]
allow_credentials=False
```

**Grafana URL:** Frontend uses environment variable
```bash
# Not required for local (defaults work)
NEXT_PUBLIC_GRAFANA_URL=http://localhost:3001
```

**Prometheus:** Scrapes backend on Docker internal network
```yaml
# infrastructure/prometheus/prometheus.yml
targets: ['backend:8000']
```

### Local Development Workflow

1. **Make Code Changes**
2. **Rebuild Affected Service:**
   ```bash
   docker compose build backend  # or frontend
   docker compose up -d backend
   ```
3. **Verify:**
   ```bash
   ./ops/verify_gate_a.sh
   ```
4. **Test in Browser:** http://localhost:3100

---

## Staging Deployment

**Purpose:** Pre-production testing, integration validation, performance testing

### Prerequisites

- Docker host or Kubernetes cluster
- Domain name or stable IP
- SSL/TLS certificates (recommended)
- Secrets management solution (e.g., AWS Secrets Manager, HashiCorp Vault)

### Environment Configuration

Create `.env.staging`:

```bash
# Backend
BEHAVIOR_API_CORS_ORIGINS=https://staging.yourdomain.com,https://staging-frontend.yourdomain.com
ENVIRONMENT=staging
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_GRAFANA_URL=https://staging-grafana.yourdomain.com
NEXT_PUBLIC_API_BASE_URL=https://staging-api.yourdomain.com

# Prometheus
PROMETHEUS_RETENTION=30d
PROMETHEUS_SCRAPE_INTERVAL=15s

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<use-secrets-manager>
GF_SERVER_ROOT_URL=https://staging-grafana.yourdomain.com
GF_AUTH_ANONYMOUS_ENABLED=false
GF_USERS_ALLOW_SIGN_UP=false
```

### Deployment Steps

1. **Provision Infrastructure:**
   - Docker host or K8s cluster
   - Load balancer / Ingress
   - Persistent volumes for Prometheus data
   - SSL certificates

2. **Set Environment Variables:**
   ```bash
   # On Docker host
   export $(cat .env.staging | xargs)

   # Or use docker-compose with env file
   docker compose --env-file .env.staging up -d
   ```

3. **Deploy Stack:**
   ```bash
   # Pull latest images
   docker compose pull

   # Deploy with staging config
   docker compose --env-file .env.staging up -d
   ```

4. **Verify Deployment:**
   ```bash
   # Run gates against staging URLs
   BASE_BACKEND=https://staging-api.yourdomain.com \
   BASE_FRONTEND=https://staging.yourdomain.com \
   ./ops/verify_gate_a.sh
   ```

5. **Configure Monitoring:**
   - Set up Grafana alerts with notification channels
   - Configure Prometheus federation (if using centralized monitoring)
   - Enable persistent storage for metrics

### Staging-Specific Considerations

**CORS:** Locked to specific origins
```python
# Backend must read from env
import os
cors_origins = os.getenv("BEHAVIOR_API_CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Secrets:** Never commit to version control
- Use environment variables from secrets manager
- Rotate credentials regularly
- Grafana admin password must be strong

**Grafana:** Disable sign-up, enable auth
```ini
GF_AUTH_ANONYMOUS_ENABLED=false
GF_USERS_ALLOW_SIGN_UP=false
```

**Prometheus:** Increase retention for testing
```yaml
# Command in docker-compose.yml
--storage.tsdb.retention.time=30d
```

---

## Production Deployment

**Purpose:** Live system serving real traffic, high availability, full monitoring

### Prerequisites

- Production-grade infrastructure (K8s recommended)
- High availability setup (multiple replicas)
- SSL/TLS certificates (required)
- Secrets management (required)
- Monitoring & alerting configured
- Backup & disaster recovery plan
- Incident response procedures

### Environment Configuration

Create `.env.production`:

```bash
# Backend
BEHAVIOR_API_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ENVIRONMENT=production
LOG_LEVEL=WARNING
SENTRY_DSN=<sentry-url>  # Optional error tracking

# Frontend
NEXT_PUBLIC_GRAFANA_URL=https://grafana.yourdomain.com
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com

# Prometheus
PROMETHEUS_RETENTION=90d
PROMETHEUS_SCRAPE_INTERVAL=15s
PROMETHEUS_EXTERNAL_URL=https://prometheus.yourdomain.com

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<strong-password-from-secrets>
GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
GF_AUTH_ANONYMOUS_ENABLED=false
GF_USERS_ALLOW_SIGN_UP=false
GF_USERS_DEFAULT_THEME=light
GF_SMTP_ENABLED=true
GF_SMTP_HOST=smtp.yourdomain.com:587
GF_SMTP_USER=<smtp-user>
GF_SMTP_PASSWORD=<smtp-password-from-secrets>

# Alerting
ALERT_NOTIFICATION_WEBHOOK=<slack-or-pagerduty-webhook>
```

### Deployment Steps

#### Option A: Docker Compose (Single Host)

1. **Provision Production Host:**
   - High-performance VM or bare metal
   - Adequate CPU/RAM (4+ cores, 16GB+ RAM)
   - SSD storage for Prometheus data
   - Automatic backups configured

2. **Deploy:**
   ```bash
   # Pull latest stable release
   git checkout v1.0.0  # or latest stable tag

   # Load secrets from secrets manager
   export $(cat .env.production | xargs)

   # Deploy
   docker compose --env-file .env.production up -d
   ```

3. **Verify:**
   ```bash
   BASE_BACKEND=https://api.yourdomain.com \
   BASE_FRONTEND=https://yourdomain.com \
   ./ops/verify_gate_a.sh
   ```

#### Option B: Kubernetes (Recommended for Production)

1. **Create Kubernetes Manifests:**

**Namespace:**
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: behavior-forecasting
```

**Backend Deployment:**
```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: behavior-forecasting
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/behavior-backend:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: BEHAVIOR_API_CORS_ORIGINS
          valueFrom:
            secretKeyRef:
              name: backend-secrets
              key: cors-origins
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**Prometheus with Persistent Storage:**
```yaml
# k8s/prometheus-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: prometheus
  namespace: behavior-forecasting
spec:
  serviceName: prometheus
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        args:
        - '--config.file=/etc/prometheus/prometheus.yml'
        - '--storage.tsdb.path=/prometheus'
        - '--storage.tsdb.retention.time=90d'
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: prometheus-data
          mountPath: /prometheus
        - name: prometheus-config
          mountPath: /etc/prometheus
  volumeClaimTemplates:
  - metadata:
      name: prometheus-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

2. **Deploy to Kubernetes:**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/backend-deployment.yaml
   kubectl apply -f k8s/frontend-deployment.yaml
   kubectl apply -f k8s/prometheus-statefulset.yaml
   kubectl apply -f k8s/grafana-deployment.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

3. **Verify:**
   ```bash
   kubectl get pods -n behavior-forecasting
   kubectl logs -n behavior-forecasting -l app=backend --tail=50
   ```

### Production-Specific Considerations

**High Availability:**
- Run 3+ backend replicas
- Run 2+ frontend replicas
- Use persistent volumes for Prometheus
- Use external database for Grafana (PostgreSQL recommended)

**Security:**
- HTTPS only (no HTTP)
- Strict CORS (specific origins only)
- Secrets in external secrets manager
- Regular security updates
- Network policies to restrict inter-service communication

**Monitoring:**
- Grafana alerts configured with notification channels
- Uptime monitoring (external service)
- Log aggregation (ELK, Loki, or CloudWatch)
- Error tracking (Sentry or similar)

**Backups:**
- Prometheus data backed up daily
- Grafana dashboards/config in version control
- Database backups (if using external Grafana DB)

**Performance:**
- Enable caching where appropriate
- Use CDN for static assets
- Optimize Docker images (multi-stage builds)
- Resource limits set appropriately

---

## Environment Variables Reference

### Backend Variables

| Variable | Required | Default | Description | Dev | Staging | Prod |
|----------|----------|---------|-------------|-----|---------|------|
| `BEHAVIOR_API_CORS_ORIGINS` | No | `*` | Comma-separated list of allowed origins | `*` | Specific domains | Specific domains |
| `ENVIRONMENT` | No | `development` | Environment name | `development` | `staging` | `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level | `DEBUG` | `INFO` | `WARNING` |
| `PORT` | No | `8000` | Backend port (internal) | `8000` | `8000` | `8000` |

### Frontend Variables

| Variable | Required | Default | Description | Dev | Staging | Prod |
|----------|----------|---------|-------------|-----|---------|------|
| `NEXT_PUBLIC_GRAFANA_URL` | No | `http://localhost:3001` | Grafana base URL | `http://localhost:3001` | `https://staging-grafana.domain.com` | `https://grafana.domain.com` |
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8100` | Backend API URL | `http://localhost:8100` | `https://staging-api.domain.com` | `https://api.domain.com` |

### Prometheus Variables

| Variable | Required | Default | Description | Dev | Staging | Prod |
|----------|----------|---------|-------------|-----|---------|------|
| `PROMETHEUS_RETENTION` | No | `15d` | Data retention period | `7d` | `30d` | `90d` |
| `PROMETHEUS_SCRAPE_INTERVAL` | No | `15s` | Scrape interval | `15s` | `15s` | `15s` |

### Grafana Variables

| Variable | Required | Default | Description | Dev | Staging | Prod |
|----------|----------|---------|-------------|-----|---------|------|
| `GF_SECURITY_ADMIN_PASSWORD` | Yes (staging/prod) | `admin` | Admin password | `admin` | From secrets | From secrets |
| `GF_SERVER_ROOT_URL` | No | Auto | Public Grafana URL | Auto | `https://staging-grafana...` | `https://grafana...` |
| `GF_AUTH_ANONYMOUS_ENABLED` | No | `true` | Allow anonymous access | `true` | `false` | `false` |
| `GF_USERS_ALLOW_SIGN_UP` | No | `true` | Allow user sign-up | `true` | `false` | `false` |

**Full Reference:** See `docs/ENVIRONMENT_VARIABLES.md`

---

## Security Considerations

### CORS Configuration

**Development:**
```python
allow_origins=["*"]  # Permissive
```

**Staging/Production:**
```python
# Read from environment
import os
cors_origins_str = os.getenv("BEHAVIOR_API_CORS_ORIGINS", "")
if cors_origins_str:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
else:
    # Fallback for dev only
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Example Production CORS:**
```bash
BEHAVIOR_API_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Secrets Management

**Never Commit:**
- `.env` files
- Passwords
- API keys
- Tokens

**Use:**
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets
- Azure Key Vault
- Google Secret Manager

**Example (Kubernetes):**
```bash
# Create secret
kubectl create secret generic backend-secrets \
  --from-literal=cors-origins=https://yourdomain.com \
  --namespace=behavior-forecasting

# Reference in deployment
env:
- name: BEHAVIOR_API_CORS_ORIGINS
  valueFrom:
    secretKeyRef:
      name: backend-secrets
      key: cors-origins
```

### Network Security

**Docker (dev/staging):**
```yaml
# docker-compose.yml
networks:
  default:
    internal: false  # Allow external access
  backend:
    internal: true   # Internal only
```

**Kubernetes:**
```yaml
# NetworkPolicy to restrict backend access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    - podSelector:
        matchLabels:
          app: prometheus
```

---

## Monitoring & Health Checks

### Health Endpoints

**Backend:**
```bash
curl https://api.yourdomain.com/health
# Expected: {"status":"ok"}
```

**Frontend:**
```bash
curl -I https://yourdomain.com/ops
# Expected: HTTP 200
```

**Prometheus:**
```bash
curl https://prometheus.yourdomain.com/-/healthy
# Expected: Prometheus is Healthy.
```

**Grafana:**
```bash
curl https://grafana.yourdomain.com/api/health
# Expected: {"database":"ok","version":"..."}
```

### Automated Monitoring

**Uptime Checks:**
- Use external service (Pingdom, UptimeRobot, StatusCake)
- Check all critical endpoints every 1-5 minutes
- Alert on downtime > 2 minutes

**Grafana Alerts:**
- Already configured in `infrastructure/grafana/provisioning/alerting/rules.yml`
- Configure notification channels in production:
  - Slack webhook
  - PagerDuty
  - Email

**Log Monitoring:**
- Aggregate logs to centralized system
- Alert on ERROR/CRITICAL log levels
- Monitor for:
  - HTTP 5xx errors
  - Database connection failures
  - High response times (> 1s)

### Gate Verification in Production

Run gates from monitoring service or cron:

```bash
#!/bin/bash
# /etc/cron.hourly/verify-gates.sh

BASE_BACKEND=https://api.yourdomain.com \
BASE_FRONTEND=https://yourdomain.com \
/path/to/ops/verify_gate_a.sh

if [ $? -ne 0 ]; then
  # Send alert
  curl -X POST https://hooks.slack.com/... \
    -d '{"text":"GATE A FAILED in production"}'
fi
```

---

## Rollback Procedures

### Docker Compose

1. **Identify Last Known Good Version:**
   ```bash
   git log --oneline | head -10
   ```

2. **Checkout Previous Version:**
   ```bash
   git checkout v0.9.0  # or commit hash
   ```

3. **Redeploy:**
   ```bash
   docker compose down
   docker compose up -d
   ```

4. **Verify:**
   ```bash
   ./ops/verify_gate_a.sh
   ./ops/verify_gate_grafana.sh
   ```

### Kubernetes

1. **Rollback Deployment:**
   ```bash
   kubectl rollout undo deployment/backend -n behavior-forecasting
   kubectl rollout undo deployment/frontend -n behavior-forecasting
   ```

2. **Check Status:**
   ```bash
   kubectl rollout status deployment/backend -n behavior-forecasting
   ```

3. **Verify:**
   ```bash
   kubectl get pods -n behavior-forecasting
   kubectl logs -n behavior-forecasting -l app=backend --tail=50
   ```

### Rollback Checklist

- [ ] Identify last known good version
- [ ] Check git tags or Docker image tags
- [ ] Rollback deployment
- [ ] Verify all services healthy
- [ ] Run both gate scripts
- [ ] Check Grafana dashboards for metrics
- [ ] Notify team of rollback
- [ ] Create incident post-mortem

---

## Troubleshooting

### Deployment Fails

**Symptom:** Docker containers fail to start

**Diagnosis:**
```bash
docker compose logs backend | tail -100
docker compose logs frontend | tail -100
```

**Common Issues:**
- Port already in use (check `docker ps`, `lsof -i :8100`)
- Missing environment variables (check `.env` file)
- Volume mount failures (check permissions)
- Image pull failures (check registry credentials)

**Resolution:**
```bash
# Stop conflicting services
docker compose down

# Clean up
docker system prune -a

# Rebuild and restart
docker compose build --no-cache
docker compose up -d
```

### CORS Errors in Production

**Symptom:** Browser console shows CORS errors

**Diagnosis:**
1. Check backend logs for CORS middleware errors
2. Verify `BEHAVIOR_API_CORS_ORIGINS` environment variable
3. Test with curl:
   ```bash
   curl -I -X OPTIONS https://api.yourdomain.com/api/forecast \
     -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST"
   ```

**Resolution:**
1. Update `BEHAVIOR_API_CORS_ORIGINS` to include all necessary origins
2. Restart backend:
   ```bash
   docker compose restart backend
   # or kubectl rollout restart deployment/backend
   ```

### Prometheus Not Scraping

**Symptom:** Grafana dashboards show "No data"

**Diagnosis:**
1. Check Prometheus targets: https://prometheus.yourdomain.com/targets
2. Check backend /metrics: https://api.yourdomain.com/metrics
3. Check Prometheus logs:
   ```bash
   docker compose logs prometheus | tail -100
   ```

**Resolution:**
- Verify backend is accessible from Prometheus (network connectivity)
- Check `infrastructure/prometheus/prometheus.yml` target configuration
- Restart Prometheus: `docker compose restart prometheus`

### Grafana Dashboards Not Loading

**Symptom:** Dashboards don't appear in Grafana UI

**Diagnosis:**
```bash
docker compose logs grafana | grep -i provision
```

**Resolution:**
1. Check volume mounts in `docker-compose.yml`
2. Verify dashboard files exist:
   ```bash
   ls infrastructure/grafana/dashboards/*.json
   ```
3. Restart Grafana:
   ```bash
   docker compose restart grafana
   # Wait 15 seconds for startup
   ```

**Further Help:** See `docs/RUNBOOK_DASHBOARDS.md` for detailed troubleshooting

---

## Continuous Deployment

### CI/CD Pipeline

**GitHub Actions Example:**

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Run Gates
      run: |
        docker compose up -d
        sleep 30
        ./ops/verify_gate_a.sh
        ./ops/verify_gate_grafana.sh

    - name: Build and Push Images
      run: |
        docker build -t myregistry/backend:${{ github.ref_name }} app/backend
        docker push myregistry/backend:${{ github.ref_name }}

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/backend \
          backend=myregistry/backend:${{ github.ref_name }} \
          -n behavior-forecasting
```

### Blue-Green Deployment

1. Deploy new version (green) alongside current (blue)
2. Test green environment with gates
3. Switch traffic to green
4. Monitor for issues
5. Keep blue for quick rollback
6. Decommission blue after stability confirmed

---

## Post-Deployment Checklist

After deploying to staging or production:

- [ ] All services healthy (`docker compose ps` or `kubectl get pods`)
- [ ] GATE A: GREEN (`./ops/verify_gate_a.sh`)
- [ ] GATE G: GREEN (`./ops/verify_gate_grafana.sh`)
- [ ] All URLs accessible (backend, frontend, Grafana, Prometheus)
- [ ] Operator Console loads: `/ops`
- [ ] Grafana dashboards load and show data
- [ ] Alerts configured and notification channels working
- [ ] SSL certificates valid (if applicable)
- [ ] Backups configured and tested
- [ ] Monitoring dashboards updated
- [ ] Team notified of deployment
- [ ] Deployment documented in changelog

---

## Additional Resources

- **Runbooks:**
  - `docs/RUNBOOK_ALERTS.md` - Alert response procedures
  - `docs/RUNBOOK_DASHBOARDS.md` - Dashboard troubleshooting
- **Configuration:**
  - `docs/ENVIRONMENT_VARIABLES.md` - All environment variables
  - `docs/OPERATOR_CONSOLE.md` - Dashboard navigation guide
- **System Status:**
  - `APP_STATUS.md` - Current capabilities and recent updates
  - `INVARIANTS.md` - System invariants and gates
- **Infrastructure:**
  - `docker-compose.yml` - Local/staging Docker configuration
  - `infrastructure/` - Prometheus, Grafana, Terraform configs

---

## Support & Escalation

**For deployment issues:**
1. Check this deployment guide
2. Check relevant runbook (`RUNBOOK_DASHBOARDS.md`)
3. Run both gate scripts and include output
4. Check service logs
5. Escalate to engineering with:
   - Environment (local/staging/production)
   - Gate script outputs
   - Service logs
   - Steps already attempted

**Emergency Rollback:** Follow [Rollback Procedures](#rollback-procedures) section above.
