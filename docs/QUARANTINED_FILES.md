# Quarantined Files

This document tracks files that have been quarantined (moved to `.quarantine/`) for potential removal.

**Status**: No files currently quarantined.

## Quarantine Policy

Files are quarantined (not deleted) when:
- They are proven unused (no imports, no references)
- They are superseded by newer versions
- They are artifacts or generated output that should not be committed

## Restoration Process

If a quarantined file is needed:
1. Move it back from `.quarantine/` to its original location
2. Update this document
3. Verify the file is actually needed

## Investigation Pending

The following files are candidates for investigation (not yet quarantined):

### Scripts Requiring Comparison
- `scripts/verify_post_work.sh` vs `scripts/post_work_verify.sh` vs `scripts/post_work_verification.sh`
- `scripts/integrity_loop.sh` vs `scripts/integrity_loop_master.sh`
- `ops/verify_changeset5_gateA.sh` vs `ops/verify_changeset5_gateA_complete.sh` vs `ops/verify_changeset5_gateA_final.sh`

**Action Required**: Compare contents, check git history, verify usage before quarantine.

## History

- 2026-01-23: Initial quarantine list created. No files quarantined yet.
