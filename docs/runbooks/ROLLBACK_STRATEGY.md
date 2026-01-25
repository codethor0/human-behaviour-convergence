# Runbook: Rollback Strategy

**Severity:** Critical
**Impact:** Revert to previous known-good state

## When to Rollback

- Critical bug introduced
- Performance degradation
- Security vulnerability
- Data corruption risk
- Invariant violations

## Rollback Procedures

### 1. Code Rollback (Git)

**Prerequisites:**
- Git repository with tagged releases
- Previous known-good commit/tag

**Procedure:**
```bash
# Identify previous good release
git tag -l  # List tags
git log --oneline -10  # Review recent commits

# Rollback to previous tag
git checkout <previous-tag>
# Or rollback to specific commit
git checkout <commit-hash>

# Force push (if necessary, with caution)
# git push --force origin main
```

**Verification:**
- Run test suite
- Verify invariants pass
- Check health endpoints
- Monitor metrics

### 2. Infrastructure Rollback (Terraform)

**Prerequisites:**
- Terraform state file
- Previous Terraform configuration

**Procedure:**
```bash
cd infra/terraform

# Review current state
terraform show

# Rollback to previous configuration
git checkout <previous-tag> infra/terraform/

# Plan rollback
terraform plan

# Apply rollback (if plan looks correct)
terraform apply
```

**Verification:**
- Verify infrastructure state
- Check resource health
- Monitor metrics
- Test connectivity

### 3. Database Rollback

**Prerequisites:**
- Database backups
- Point-in-time recovery capability

**Procedure:**
```bash
# Stop application
systemctl stop backend

# Restore database from backup
# (Specific commands depend on database type)

# For PostgreSQL:
pg_restore -d hbc /path/to/backup.dump

# For SQLite:
cp /path/to/backup.db /app/data/hbc.db

# Restart application
systemctl start backend
```

**Verification:**
- Verify database integrity
- Check data consistency
- Test application connectivity
- Monitor for errors

### 4. Configuration Rollback

**Prerequisites:**
- Configuration backups
- Version-controlled configuration

**Procedure:**
```bash
# Restore previous configuration
cp /path/to/backup/config.env /app/.env

# Or restore from version control
git checkout <previous-tag> .env

# Restart application
systemctl restart backend
```

**Verification:**
- Verify configuration loaded
- Check environment variables
- Test application functionality
- Monitor logs

## Rollback Decision Matrix

| Issue Type | Rollback Type | Time to Rollback | Risk Level |
|------------|---------------|------------------|------------|
| Critical Bug | Code | 5-10 minutes | Low |
| Performance Degradation | Code + Config | 10-15 minutes | Medium |
| Security Vulnerability | Code + Infra | 15-30 minutes | High |
| Data Corruption | Database | 30-60 minutes | High |
| Invariant Violation | Code | 5-10 minutes | Low |

## Post-Rollback Procedures

### 1. Verify System Health (5 minutes)

- Check health endpoints
- Verify metrics
- Review logs
- Test critical functionality

### 2. Document Rollback (10 minutes)

- Record rollback reason
- Document rollback procedure used
- Note any issues encountered
- Update runbook if needed

### 3. Root Cause Analysis (1-2 hours)

- Investigate root cause
- Identify prevention measures
- Update tests if needed
- Update documentation

### 4. Re-deploy Fixed Version (after fix)

- Fix root cause
- Test fix thoroughly
- Deploy fixed version
- Monitor closely

## Prevention

1. **Automated Testing:** Comprehensive test suite before deployment
2. **Staged Rollouts:** Deploy to staging before production
3. **Feature Flags:** Use feature flags for risky changes
4. **Monitoring:** Monitor metrics and logs closely after deployment
5. **Backups:** Regular backups of database and configuration

## Contacts

- **On-Call Engineer:** [Contact Info]
- **SRE Team:** [Contact Info]
- **DevOps Team:** [Contact Info]
- **Incident Commander:** [Contact Info]
