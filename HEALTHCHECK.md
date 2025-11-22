# Repository Health Check (Dry Run)

## Summary
- **Mode:** dry-run (no changes applied)
- **Risk level:** conservative
- **Scope:** american spelling standardization follow-up + repo hygiene snapshot
- **Default branch:** `main`
- **Current branch:** `chore/spelling-behavior-standardization`

## Inventory
| Area | Details |
| --- | --- |
| Languages | Python (backend CLI/tests), TypeScript/React (Next.js frontend), Markdown/HTML docs, Mermaid diagrams |
| Package managers | `pip` (`requirements.txt`, `app/backend/requirements.txt`), npm (Next.js `package.json`) |
| CI workflows | `.github/workflows/app-ci.yml`, `ci.yml`, `test.yml`, `render-diagram.yml`, `check-branch-protection.yml`, `emoji-check.yml`, `deploy-pages.yml`, `quality-gates.yml`, `scorecard.yml` |
| Containers/IaC | `Dockerfile`, `docker-compose.yml` |
| Notebooks | `notebooks/demo.ipynb` (markdown updated for American English) |

## Baseline Status
- `ruff check .` (targeted modules) **passed** after spelling updates.
- `python .github/scripts/check_american_spelling.py` **passed** enforcing the new style.
- `pytest --maxfail=1 --disable-warnings` **passed** (35 tests, ~34 minutes).
- Pre-commit enhanced with `enforce-american-spelling` hook.

## Key Issues Observed
- Legacy slugs still use `behaviour`; intentionally excluded from spelling guard to avoid breaking URLs and package names.
- Large test runtime (~34 min) remains; consider splitting smoke vs full suite in future cleanup.

## Proposed PRs
| Title | Scope | Estimated Diff | Risk | Rollback |
| --- | --- | --- | --- | --- |
| `docs: standardize spelling to American English (behavior/behavioral)` | README, docs, frontend/CLI UI text, diagrams | ~80 additions / 75 deletions | Low | Revert commit (string changes only) |
| `chore(pre-commit): add american spelling guard` | New `.github/scripts/check_american_spelling.py`, hook wiring | +1 new script, +6 lines in config | Low | Remove hook + script |

## Follow-ups / Open Questions
- Consider caching or sharding test runs (Pytest currently >30 minutes).
- Monitor pre-commit hook for false positives as contributors touch legacy slugs.
- Future health pass: revisit Ruff full run (currently X errors suppressed via ignore codes in CI).

## Next Recommended Cadence
- Re-run health sweep monthly or before major releases, especially if new contributors join.
