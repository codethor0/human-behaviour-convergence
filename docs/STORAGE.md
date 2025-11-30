# Storage Design

**Date:** 2025-01-XX
**Version:** 1.0

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## Overview

The Human Behaviour Convergence platform uses **SQLite** as a lightweight, file-based database for storing forecast history and metrics. SQLite is ideal for local development, testing, and small-scale deployments as it requires no separate database server and has zero configuration overhead.

---

## Database Schema

### Forecasts Table

Stores individual forecast records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-incremented unique identifier |
| `timestamp` | TEXT | ISO format timestamp of the forecast |
| `region_name` | TEXT | Human-readable region name |
| `latitude` | REAL | Latitude coordinate (-90 to 90) |
| `longitude` | REAL | Longitude coordinate (-180 to 180) |
| `model_name` | TEXT | Name of forecasting model (e.g., "ExponentialSmoothing") |
| `behavior_index` | REAL | Behavior index value (0.0 to 1.0) |
| `sub_indices` | TEXT | JSON string of sub-index values |
| `metadata` | TEXT | JSON string of additional metadata |
| `version` | TEXT | Version identifier (default: "1.0") |
| `created_at` | TEXT | ISO timestamp when record was created |

**Indexes:**
- `idx_forecasts_timestamp` on `timestamp`
- `idx_forecasts_region` on `region_name`

### Metrics Table

Stores performance metrics for forecasts.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-incremented unique identifier |
| `forecast_id` | INTEGER | Foreign key to `forecasts.id` |
| `metric_name` | TEXT | Name of the metric (e.g., "mae", "rmse", "mape") |
| `metric_value` | REAL | Numeric value of the metric |
| `computed_at` | TEXT | ISO timestamp when metric was computed |

**Indexes:**
- `idx_metrics_forecast_id` on `forecast_id`

---

## Usage

### Initialization

```python
from app.storage import ForecastDB

# Use default path (data/hbc.db)
db = ForecastDB()

# Or specify custom path
db = ForecastDB(db_path="/path/to/custom.db")

# Or use environment variable
# HBC_DB_PATH=/path/to/db.db
db = ForecastDB()  # Will use HBC_DB_PATH
```

### Saving Forecasts

```python
forecast_id = db.save_forecast(
    region_name="New York City",
    latitude=40.7128,
    longitude=-74.0060,
    model_name="ExponentialSmoothing",
    behavior_index=0.65,
    sub_indices={
        "economic_stress": 0.45,
        "environmental_stress": 0.35,
        "mobility_activity": 0.60,
        "digital_attention": 0.50,
        "public_health_stress": 0.40,
    },
    metadata={
        "forecast_horizon": 7,
        "historical_data_points": 30,
        "sources": ["yfinance", "openmeteo.com"],
    },
)

# Save metrics for the forecast
db.save_metrics(forecast_id, {
    "mae": 78.5,
    "rmse": 112.3,
    "mape": 0.95,
    "crps": 0.072,
    "coverage_95": 1.0,
    "bias": 5.2,
})
```

### Retrieving Forecasts

```python
# Get all forecasts (limit 100)
forecasts = db.get_forecasts()

# Get forecasts for a specific region
nyc_forecasts = db.get_forecasts(region_name="New York City", limit=50)

# Get metrics for a forecast
metrics = db.get_metrics(forecast_id=1)

# Export to pandas DataFrame
df = db.export_to_dataframe()
```

---

## Database File Location

**Default:** `data/hbc.db` (relative to project root)

**Environment Variable:** `HBC_DB_PATH` (if set, overrides default)

**Docker:** The database file should be persisted via volume mounts:

```yaml
volumes:
  - ./data:/app/data  # Persist database across container restarts
```

---

## CI/CD Considerations

For CI environments, the database is **optional**:

- Tests can use in-memory SQLite (`:memory:`) or temporary files
- Database path can be set via environment variable
- If database is not available, the application should degrade gracefully

**Example test setup:**

```python
import tempfile
import os

def test_forecast_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = ForecastDB(db_path=db_path)
        # ... test code ...
    finally:
        os.unlink(db_path)
```

---

## Migration and Versioning

**Current Version:** 1.0

Future schema changes should:

1. Increment version number in `ForecastDB.save_forecast(version=...)`
2. Add migration scripts in `app/storage/migrations/` if needed
3. Update this documentation

---

## Limitations

1. **File-based:** SQLite is a file database, not suitable for multi-server deployments
2. **Write Concurrency:** Limited write concurrency (fine for low-volume use)
3. **Size Limits:** Practical limit around 100GB (more than sufficient for forecast history)
4. **No Remote Access:** Cannot be accessed remotely without additional tooling

---

## Future Enhancements

1. **Migration System:** Automated schema migrations
2. **Backup/Restore:** Utilities for database backup and restoration
3. **Analytics Queries:** Pre-defined queries for common analytics needs
4. **Archival:** Move old forecasts to archive tables/CSV for performance

---

**Maintainer:** Thor Thor (codethor@gmail.com)
