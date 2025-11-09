# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Backend README notes covering cache configuration, CSV normalisation, and test workflow.

### Changed
- FastAPI backend now normalises CSV columns, enforces cache eviction/TTL consistently, and keeps stub responses stable.
- Introduced a module shim so overrides of `RESULTS_DIR` / `MAX_CACHE_SIZE` stay in sync between `app.main` and the backend implementation.

### Planned
- Jupyter notebook with synthetic data demo
- Unit tests and CI workflow for tests
- Results folder with example CSVs (ground truth, forecasts, metrics)
- Python package structure with `requirements.txt`
- Hyperlinked Mermaid diagram (nodes link to implementation)

---

## [0.1.0] - 2025-11-03

### Added
- Initial Mermaid diagram (`diagram/behaviour-convergence.mmd`)
- GitHub Actions workflow for auto-rendering SVG/PNG
- Community health files: CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, SUPPORT
- Issue and PR templates
- Dependabot and OpenSSF Scorecard workflows
- CODEOWNERS file
- ETHICS.md with privacy and IRB details
- CITATION.cff for DOI and citation support
- Expanded README with elevator pitch, roadmap, and quick start

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- Enabled Dependabot for GitHub Actions
- OpenSSF Scorecard workflow for supply-chain security

---

## Notes

- **v0.1.0** is a proof-of-concept release. The full dataset and production model are not yet public.
- For questions or contributions, see [CONTRIBUTING.md](./CONTRIBUTING.md).
