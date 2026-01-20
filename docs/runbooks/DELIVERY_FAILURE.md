# Runbook: Delivery Failure

**Severity:** Medium
**Impact:** Notification delivery failing (all channels or specific channel)

## Symptoms

- High `notification_failure_count` metric
- Notification delivery errors in logs
- No notifications received by users
- Alerts still being persisted

## Detection

- Monitor `notification_failure_count` metric
- Check notification delivery logs
- Review error messages
- Monitor notification success rate

## Immediate Response

### Step 1: Identify Failure Pattern (2 minutes)

```bash
# Check logs for notification errors
grep "Failed to send.*notification" /var/log/app/backend.log

# Check specific channel errors
grep -i "email\|slack\|webhook" /var/log/app/backend.log | grep -i "error\|failed"
```

**Common Failure Patterns:**
- Authentication failures (SMTP credentials)
- Network timeouts
- Invalid webhook URLs
- Rate limiting from provider

### Step 2: Check Channel Configuration (1 minute)

**Verify Environment Variables:**
```bash
# Email
echo $SMTP_HOST
echo $SMTP_USER
echo $SMTP_FROM_EMAIL

# Webhook
echo $WEBHOOK_URL

# Slack
echo $SLACK_WEBHOOK_URL
```

**Expected:** All required variables set and non-empty.

### Step 3: Test Channel Connectivity (2 minutes)

**Email (SMTP):**
```bash
# Test SMTP connection
telnet $SMTP_HOST $SMTP_PORT
```

**Webhook:**
```bash
# Test webhook endpoint
curl -X POST $WEBHOOK_URL -H "Content-Type: application/json" -d '{"test": true}'
```

**Slack:**
```bash
# Test Slack webhook
curl -X POST $SLACK_WEBHOOK_URL -H "Content-Type: application/json" -d '{"text": "Test"}'
```

### Step 4: Fix Configuration (if needed)

1. **Update Environment Variables:** Set correct values
2. **Restart Backend Service:** Apply new configuration
3. **Verify Configuration:** Re-check environment variables

### Step 5: Disable Channel (if fix not immediate)

If configuration fix requires time:

```bash
# Disable affected channel
export ALERTS_EMAIL_ENABLED=false  # or appropriate channel
# Restart backend service
```

**Expected Result:** Channel disabled, other channels continue, alerts still persisted.

## Resolution

### Step 1: Fix Root Cause

**Common Fixes:**
- Update SMTP credentials
- Fix webhook URL
- Update Slack webhook URL
- Fix network connectivity
- Resolve provider rate limiting

### Step 2: Re-enable Channel (after fix)

```bash
export ALERTS_EMAIL_ENABLED=true  # or appropriate channel
# Restart backend service
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

- Record root cause
- Document configuration changes
- Update runbook if needed

## Prevention

1. **Configuration Validation:** Validate configuration on startup
2. **Health Checks:** Periodic channel health checks
3. **Monitoring:** Alert on notification failure rate
4. **Documentation:** Keep configuration documentation updated

## Rollback

If channel continues to fail after fix:

1. Re-disable channel
2. Investigate root cause more deeply
3. Check provider status
4. Contact on-call engineer if needed

## Contacts

- **On-Call Engineer:** [Contact Info]
- **SRE Team:** [Contact Info]
- **Provider Support:** [Contact Info]
