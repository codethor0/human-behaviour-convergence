# Runbook: Alert Storm

**Severity:** High
**Impact:** High volume of alerts triggering excessive notifications

## Symptoms

- High volume of alerts in short time window
- Notification channels overwhelmed
- Database write load elevated
- User complaints about alert spam

## Detection

- Monitor `notification_success_count` metric
- Check alert persistence rate
- Review notification failure logs
- Monitor database write latency

## Immediate Response

### Step 1: Enable Global Kill Switch (30 seconds)

**Via Environment Variable:**
```bash
export ALERTS_ENABLED=false
# Restart backend service
```

**Via API (if available):**
```python
from app.core.operational import get_operational_manager
manager = get_operational_manager()
manager.disable_alerts()
```

**Expected Result:** Alerts stop being persisted and notified immediately. Analytics continue normally.

### Step 2: Verify Kill Switch Active (10 seconds)

```bash
# Check logs for kill switch confirmation
grep "Alerts globally disabled" /var/log/app/backend.log
```

**Expected Result:** Log entry confirming alerts disabled.

### Step 3: Review Alert Definitions (5 minutes)

1. Check alert thresholds
2. Review persistence requirements
3. Verify rate limits are configured
4. Check for misconfigured alert definitions

**Common Issues:**
- Thresholds too low
- Persistence requirements too short
- Rate limits not configured
- Duplicate alert definitions

### Step 4: Adjust Alert Definitions (if needed)

1. Increase thresholds
2. Increase persistence requirements
3. Reduce alert sensitivity
4. Consolidate duplicate alerts

## Resolution

### Step 1: Re-enable Alerts (after fixes)

**Via Environment Variable:**
```bash
export ALERTS_ENABLED=true
# Restart backend service
```

**Via API:**
```python
manager = get_operational_manager()
manager.enable_alerts()
```

### Step 2: Monitor Alert Volume (15 minutes)

- Check alert generation rate
- Monitor notification success rate
- Verify no alert storm recurrence

### Step 3: Document Incident

- Record root cause
- Document alert definition changes
- Update runbook if needed

## Prevention

1. **Alert Definition Review:** Regular review of alert thresholds
2. **Rate Limiting:** Ensure rate limits are configured (default: 24h)
3. **Testing:** Test alert definitions with historical data before deployment
4. **Monitoring:** Set up alerts on alert generation rate

## Rollback

If alert storm persists after re-enabling:

1. Re-disable alerts globally
2. Investigate root cause more deeply
3. Consider disabling specific alert types
4. Contact on-call engineer if needed

## Contacts

- **On-Call Engineer:** [Contact Info]
- **SRE Team:** [Contact Info]
- **Security Team:** [Contact Info]
