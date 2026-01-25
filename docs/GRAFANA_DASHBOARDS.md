# Grafana Dashboards

This document catalogs all Grafana dashboards available in the HBC system.

## Access

Dashboards are accessible via Grafana at `http://localhost:3001` (default credentials: admin/admin).

All dashboards are provisioned automatically from `infra/grafana/dashboards/*.json` files.

## Dashboard Catalog

### 1. Public Overview (`public-overview`)

**Purpose**: Executive-level overview of system status and key metrics.

**Panels**:
- Regions with Metrics Count
- Warm-up Progress Ratio
- Active Data Sources Count
- Failing Data Sources Count
- Top 10 Regions by Behavior Index (table)
- Top 10 Biggest 24h Change (delta table)
- Risk Tier by Region (state timeline)
- Data Source Health Summary (table)

**Tags**: `public`, `overview`, `executive`

**Time Range**: Last 7 days

**Refresh**: 30s

---

### 2. Regional Deep Dive (`regional-deep-dive`)

**Purpose**: Explainability dashboard - understand why a specific region scores as it does.

**Variables**:
- `region` (single select) - Populated from `label_values(behavior_index, region)`

**Panels**:
- Behavior Index Time Series
- Parent Sub-Indices Time Series
- Current Parent Sub-Index Values (bar gauge)
- Top Child Sub-Index Contributors (table)
- Global vs Regional Index Classification (table)

**Tags**: `regional`, `deep-dive`, `explainability`

**Time Range**: Last 30 days

**Refresh**: 30s

**Note**: The Global vs Regional classification panel explicitly labels which indices are expected to be constant (global) vs vary by region (regional).

---

### 3. Geo Map - Regional Stress (`geo-map`)

**Purpose**: Spatial visualization of behavior index and regional stress metrics.

**Panels**:
- Behavior Index by Region (Geomap)
- Regional Child Metrics (Geomap, if available)

**Implementation**: Uses Grafana Geomap panel with lat/lon coordinates from static CSV data source.

**Tags**: `geo`, `map`, `spatial`

**Time Range**: Last 1 hour (for current snapshot)

**Refresh**: 30s

---

### 4. Data Sources Health (`data-sources-health`)

**Purpose**: Monitor the health and status of all data sources.

**Panels**:
- Data Source Status Table (current status per source)
- Data Source Status Over Time (time series per source)

**Tags**: `health`, `monitoring`, `data-sources`

**Time Range**: Last 7 days

**Refresh**: 30s

---

### 5. Additional Dashboards

The following dashboards are also available:

- **Global Behavior Index** (`global-behavior-index`) - Global/national-level behavior index trends
- **Historical Trends** (`historical-trends`) - Long-term historical analysis
- **Regional Comparison** (`regional-comparison`) - Side-by-side comparison of multiple regions
- **Risk Regimes** (`risk-regimes`) - Risk tier classification and transitions
- **Subindex Deep Dive** (`subindex-deep-dive`) - Detailed sub-index analysis
- **Forecast Summary** (`forecast-summary`) - Forecast generation statistics
- **Regional Signals** (`regional-signals`) - Regional signal contributions

## Dashboard Best Practices

All dashboards follow these best practices:

1. **Performance**: Minimal query count, aggregated PromQL where possible
2. **Maintainability**: Versioned JSON files, stable UIDs and titles
3. **Usability**: Clear labels, sensible defaults, appropriate time ranges
4. **Transformations**: Use Grafana transformations (Labels to fields, Reduce, Join) instead of backend hacks
5. **Panel Types**: Appropriate panel types for data (timeseries, table, stat, geomap, etc.)

## Global vs Regional Indices

See `docs/datasets/GLOBAL_VS_REGIONAL_INDICES.md` for detailed classification of which indices are:
- **Global**: Expected to be identical across regions (e.g., `mobility_activity`, `digital_attention`)
- **Regional**: Must vary across regions (e.g., `environmental_stress`, `fuel_stress`, `drought_stress`)
- **Mixed**: Combination of global and regional components (e.g., `economic_stress`)

The Regional Deep Dive dashboard includes a panel that explicitly labels this classification to prevent confusion.

## Metrics Reference

All dashboards query Prometheus metrics exported by the backend:

- `behavior_index{region="..."}` - Composite behavior index
- `parent_subindex_value{parent="...", region="..."}` - Parent sub-index values
- `child_subindex_value{child="...", parent="...", region="..."}` - Child sub-index values
- `data_source_status{source="..."}` - Data source health (1=active, 0=inactive)
- `hbc_regions_with_metrics_count` - Count of regions with metrics
- `hbc_warmup_progress_ratio` - Warm-up progress (0-1)

## Troubleshooting

### Dashboards Not Appearing

1. Check Grafana is running: `docker compose ps`
2. Verify provisioning: Check `infra/grafana/provisioning/dashboards/dashboards.yml`
3. Check volume mounts: Verify `docker-compose.yml` mounts dashboard directory
4. Check Grafana logs: `docker compose logs grafana`

### Panels Showing No Data

1. Verify metrics exist: `curl http://localhost:8100/metrics | grep behavior_index`
2. Check Prometheus scraping: `curl http://localhost:9090/api/v1/targets`
3. Verify time range: Ensure time range includes data points
4. Check query syntax: Verify PromQL queries in panel JSON

### Regional Variance Issues

1. Check which index you're viewing (global vs regional)
2. Verify regional data sources are configured
3. Check `docs/datasets/GLOBAL_VS_REGIONAL_INDICES.md` for expected behavior
4. Run variance probe: `python scripts/variance_probe.py`

## Adding New Dashboards

1. Create dashboard JSON in `infra/grafana/dashboards/`
2. Use stable UID (lowercase, hyphens)
3. Follow existing dashboard structure
4. Test locally: `docker compose restart grafana`
5. Verify in Grafana UI
6. Update this document

## References

- Grafana Documentation: https://grafana.com/docs/grafana/latest/
- Prometheus Querying: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Dashboard Best Practices: https://docs.aws.amazon.com/grafana/latest/userguide/v10-dash-bestpractices.html
