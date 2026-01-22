# Grafana Region Dropdown Warm-Up Explanation

## How the Region Dropdown Works

The Grafana region dropdown variable is populated using:

```
label_values(behavior_index, region)
```

This Prometheus query returns **only regions that currently have metrics** in Prometheus.

## Why You Might See "Only Minnesota" or Few Regions

### Warm-Up Period

When the stack first starts:

1. **Background metrics population** runs asynchronously (takes ~5-10 minutes)
2. **Grafana dashboards** load immediately but may only show regions that already have metrics
3. **If you generate a forecast** for a specific region, that region's metrics appear immediately
4. **Other regions** appear as the background job completes

### Expected Timeline

- **0-2 minutes**: Only regions with manually generated forecasts (if any)
- **2-10 minutes**: Background job populates US states + key global cities
- **10+ minutes**: Full region list available in dropdown

## How to Verify

### Check Prometheus Directly

```bash
# Count regions with metrics
curl -s "http://localhost:9090/api/v1/label/region/values" | jq 'length'

# List available regions
curl -s "http://localhost:9090/api/v1/label/region/values" | jq -r '.[]'
```

### Check Backend Metrics

```bash
# Count distinct regions in backend metrics
curl -s http://localhost:8100/metrics | grep 'behavior_index{region=' | sed 's/.*region="\([^"]*\)".*/\1/' | sort -u | wc -l
```

## Solutions

### Option 1: Wait for Warm-Up (Recommended)

Simply wait 5-10 minutes after stack startup for the background metrics population to complete.

### Option 2: Generate Forecasts Manually

Generate forecasts for specific regions via the `/forecast` page to immediately populate their metrics:

1. Go to `/forecast`
2. Select a region
3. Click "Generate Forecast"
4. That region's metrics will appear in Grafana immediately

### Option 3: Check Metrics Status

Use the backend metrics endpoint to see which regions have metrics:

```bash
curl http://localhost:8100/metrics | grep behavior_index | grep region=
```

## Frontend Region Dropdown vs Grafana Variable

**Important distinction**:

- **Frontend region dropdown** (`/forecast`, `/playground`, `/live`): Populated from `/api/forecasting/regions` (all 62 regions, always available)
- **Grafana dashboard variable**: Populated from Prometheus metrics (only regions with metrics, depends on warm-up)

This means:
- You can **always** select any region in the frontend UI
- But Grafana dashboards will only show data for regions that have metrics
- After generating a forecast, that region's metrics appear in Grafana

## Troubleshooting

### If dropdown shows no regions:

1. Check Prometheus is scraping: `curl http://localhost:9090/-/ready`
2. Check backend metrics: `curl http://localhost:8100/metrics | head -20`
3. Check background job logs: `docker compose logs backend | grep "metrics population"`
4. Generate a forecast manually to trigger metrics emission

### If dropdown shows only one region:

- This is normal during warm-up
- Wait 5-10 minutes for background job to complete
- Or generate forecasts for additional regions manually

## Configuration

To disable background metrics population (not recommended):

```bash
HBC_POPULATE_ALL_REGION_METRICS=0 docker compose up
```

This will make the warm-up period longer, as metrics only appear when forecasts are manually generated.
