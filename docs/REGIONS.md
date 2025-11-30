# Regions Documentation

**Date:** 2025-01-XX
**Version:** 1.0

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## Overview

The Human Behaviour Convergence platform supports behavioral forecasting for multiple geographic regions, including global cities and US states. Regions are defined with standardized identifiers, coordinates, and metadata to enable consistent forecasting across different locations.

---

## Region Model

Each region is represented by a `Region` object with the following fields:

- **id** (str): Unique identifier (e.g., "us_mn", "city_nyc")
- **name** (str): Human-readable name (e.g., "Minnesota", "New York City")
- **country** (str): ISO country code (e.g., "US", "GB", "JP")
- **region_type** (str): Type of region - one of "city", "state", or "country"
- **latitude** (float): Geographic latitude (-90 to 90)
- **longitude** (float): Geographic longitude (-180 to 180)

---

## Supported Regions

### Global Cities

The platform includes three major global cities:

1. **New York City** (city_nyc)
   - Country: US
   - Coordinates: 40.7128, -74.0060

2. **London** (city_london)
   - Country: GB
   - Coordinates: 51.5074, -0.1278

3. **Tokyo** (city_tokyo)
   - Country: JP
   - Coordinates: 35.6762, 139.6503

### US States

All 50 US states plus the District of Columbia are supported:

- Alabama (us_al)
- Alaska (us_ak)
- Arizona (us_az)
- Arkansas (us_ar)
- California (us_ca)
- Colorado (us_co)
- Connecticut (us_ct)
- Delaware (us_de)
- District of Columbia (us_dc)
- Florida (us_fl)
- Georgia (us_ga)
- Hawaii (us_hi)
- Idaho (us_id)
- Illinois (us_il)
- Indiana (us_in)
- Iowa (us_ia)
- Kansas (us_ks)
- Kentucky (us_ky)
- Louisiana (us_la)
- Maine (us_me)
- Maryland (us_md)
- Massachusetts (us_ma)
- Michigan (us_mi)
- Minnesota (us_mn)
- Mississippi (us_ms)
- Missouri (us_mo)
- Montana (us_mt)
- Nebraska (us_ne)
- Nevada (us_nv)
- New Hampshire (us_nh)
- New Jersey (us_nj)
- New Mexico (us_nm)
- New York (us_ny)
- North Carolina (us_nc)
- North Dakota (us_nd)
- Ohio (us_oh)
- Oklahoma (us_ok)
- Oregon (us_or)
- Pennsylvania (us_pa)
- Rhode Island (us_ri)
- South Carolina (us_sc)
- South Dakota (us_sd)
- Tennessee (us_tn)
- Texas (us_tx)
- Utah (us_ut)
- Vermont (us_vt)
- Virginia (us_va)
- Washington (us_wa)
- West Virginia (us_wv)
- Wisconsin (us_wi)
- Wyoming (us_wy)

**Total:** 51 US regions (50 states + DC) + 11 global cities = **62 regions**

---

## API Endpoints

### GET /api/forecasting/regions

Returns a list of all available regions.

**Response:**
```json
[
  {
    "id": "us_mn",
    "name": "Minnesota",
    "country": "US",
    "region_type": "state",
    "latitude": 46.7296,
    "longitude": -94.6859
  },
  {
    "id": "city_nyc",
    "name": "New York City",
    "country": "US",
    "region_type": "city",
    "latitude": 40.7128,
    "longitude": -74.0060
  }
]
```

### POST /api/forecast

Generate a forecast for a region. Accepts either:

1. **region_id** (recommended): Use a predefined region identifier
2. **latitude + longitude**: Use raw coordinates

**Request with region_id:**
```json
{
  "region_id": "us_mn",
  "region_name": "Minnesota",
  "days_back": 30,
  "forecast_horizon": 7
}
```

**Request with coordinates:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "region_name": "New York City",
  "days_back": 30,
  "forecast_horizon": 7
}
```

---

## Implementation

Regions are defined in `app/core/regions.py`:

- `GLOBAL_CITIES`: List of global city regions
- `US_STATES`: List of all 50 US states + DC
- `get_all_regions()`: Returns all regions, sorted by type and name
- `get_region_by_id(region_id)`: Looks up a region by ID

---

## Usage Examples

### Python

```python
from app.core.regions import get_all_regions, get_region_by_id

# Get all regions
all_regions = get_all_regions()
print(f"Total regions: {len(all_regions)}")

# Look up a specific region
minnesota = get_region_by_id("us_mn")
if minnesota:
    print(f"{minnesota.name}: {minnesota.latitude}, {minnesota.longitude}")
```

### API

```bash
# List all regions
curl http://localhost:8100/api/forecasting/regions

# Generate forecast for Minnesota
curl -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": "us_mn",
    "region_name": "Minnesota",
    "days_back": 30,
    "forecast_horizon": 7
  }'
```

---

## Future Extensions

The region system is designed to support future expansion:

- Additional global cities
- International states/provinces
- Country-level regions
- Custom region definitions via configuration

---

**Maintainer:** Thor Thor (codethor@gmail.com)
**Last Updated:** 2025-01-XX
