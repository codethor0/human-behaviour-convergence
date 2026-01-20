# Runbook: Kill Switch Procedure

**Severity:** Critical
**Impact:** Immediate shutdown of alert processing

## When to Use Kill Switches

- Alert storm detected
- Security incident
- Provider outage affecting all channels
- System degradation
- Emergency maintenance

## Kill Switch Types

### 1. Global Alert Kill Switch

**Purpose:** Disable all alert processing (persistence + notifications)

**Method 1: Environment Variable**
```bash
export ALERTS_ENABLED=false
# Restart backend service
```

**Method 2: API (if available)**
```python
from app.core.operational import get_operational_manager
manager = get_operational_manager()
manager.disable_alerts()
```

**Effect:**
- Alerts stop being persisted
- Notifications stop immediately
- Analytics continue normally
- API responses still include alert analysis (not persisted/notified)

**Verification:**
```bash
# Check logs
grep "Alerts globally disabled" /var/log/app/backend.log
```

### 2. Per-Channel Kill Switches

**Purpose:** Disable specific notification channel

**Email Channel:**
```bash
export ALERTS_EMAIL_ENABLED=false
# Restart backend service
```

**Webhook Channel:**
```bash
export ALERTS_WEBHOOK_ENABLED=false
# Restart backend service
```

**Slack Channel:**
```bash
export ALERTS_SLACK_ENABLED=false
# Restart backend service
```

**Via API:**
```python
manager = get_operational_manager()
manager.disable_channel("email")  # or "webhook" or "slack"
```

**Effect:**
- Specific channel disabled
- Other channels continue operating
- Alerts still persisted
- Analytics unaffected

## Re-enabling Kill Switches

### Global Alert Re-enable

```bash
export ALERTS_ENABLED=true
# Restart backend service
```

**Via API:**
```python
manager = get_operational_manager()
manager.enable_alerts()
```

### Per-Channel Re-enable

```bash
export ALERTS_EMAIL_ENABLED=true  # or appropriate channel
# Restart backend service
```

**Via API:**
```python
manager = get_operational_manager()
manager.enable_channel("email")  # or appropriate channel
```

## Verification

### Verify Kill Switch Active

```bash
# Check logs for kill switch confirmation
grep "Alerts globally disabled\|Channel disabled" /var/log/app/backend.log

# Check metrics (should show zero notifications)
curl http://localhost:8000/api/metrics | grep notification
```

### Verify Kill Switch Inactive

```bash
# Check logs for re-enable confirmation
grep "Alerts globally enabled\|Channel enabled" /var/log/app/backend.log

# Test alert processing
# Trigger test alert and verify notification received
```

## Safety Guarantees

1. **Analytics Unaffected:** Kill switches do not affect analytics computation
2. **Zero Numerical Drift:** Kill switches are purely operational, no numerical changes
3. **Immediate Effect:** Kill switches take effect immediately
4. **Reversible:** Kill switches can be re-enabled safely
5. **Auditable:** All kill switch actions are logged

## Emergency Contacts

- **On-Call Engineer:** [Contact Info]
- **SRE Team:** [Contact Info]
- **Security Team:** [Contact Info]
- **Incident Commander:** [Contact Info]
