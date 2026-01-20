# Runbook: Provider Outage

**Severity:** Medium
**Impact:** External provider (SMTP, Slack, webhook) unavailable

## Symptoms

- Notification delivery failures
- Provider-specific error messages in logs
- High `notification_failure_count` metric
- Provider status page shows outage

## Detection

- Monitor `notification_failure_count` metric
- Check notification delivery logs
- Review provider status pages
- Monitor error rates by channel

## Immediate Response

### Step 1: Identify Affected Channel (1 minute)

```bash
# Check logs for provider-specific errors
grep "Failed to send" /var/log/app/backend.log | grep -i "smtp\|slack\|webhook"
```

**Common Providers:**
- SMTP (email)
- Slack webhook
- Custom webhook endpoint

### Step 2: Disable Affected Channel (30 seconds)

**Via Environment Variable:**
```bash
# For email
export ALERTS_EMAIL_ENABLED=false

# For Slack
export ALERTS_SLACK_ENABLED=false

# For webhook
export ALERTS_WEBHOOK_ENABLED=false

# Restart backend service
```

**Via API:**
```python
from app.core.operational import get_operational_manager
manager = get_operational_manager()
manager.disable_channel("email")  # or "slack" or "webhook"
```

**Expected Result:** Affected channel stops sending. Other channels continue operating. Alerts still persisted.

### Step 3: Verify Channel Disabled (10 seconds)

```bash
# Check logs for channel disable confirmation
grep "Channel disabled" /var/log/app/backend.log
```

**Expected Result:** Log entry confirming channel disabled.

### Step 4: Monitor Provider Status (ongoing)

- Check provider status page
- Monitor provider recovery
- Review provider incident reports

## Resolution

### Step 1: Verify Provider Recovery (5 minutes)

- Check provider status page (should show "operational")
- Test provider connectivity manually
- Verify no ongoing incidents

### Step 2: Re-enable Channel (30 seconds)

**Via Environment Variable:**
```bash
export ALERTS_EMAIL_ENABLED=true  # or appropriate channel
# Restart backend service
```

**Via API:**
```python
manager = get_operational_manager()
manager.enable_channel("email")  # or appropriate channel
```

### Step 3: Test Notification Delivery (2 minutes)

- Trigger test alert
- Verify notification received
- Check logs for successful delivery

### Step 4: Monitor Channel Health (15 minutes)

- Check notification success rate
- Monitor error rates
- Verify no recurrence

### Step 5: Document Incident

- Record provider outage duration
- Document impact
- Update runbook if needed

## Prevention

1. **Multi-Channel Redundancy:** Use multiple notification channels
2. **Provider Monitoring:** Monitor provider status pages
3. **Retry Logic:** Implement exponential backoff retries
4. **Fallback Channels:** Configure fallback notification channels

## Rollback

If channel continues to fail after re-enabling:

1. Re-disable channel
2. Investigate provider connectivity
3. Check network/firewall rules
4. Contact provider support if needed

## Contacts

- **On-Call Engineer:** [Contact Info]
- **SRE Team:** [Contact Info]
- **Provider Support:** [Contact Info]
