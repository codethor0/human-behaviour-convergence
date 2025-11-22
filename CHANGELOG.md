# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Backend README notes covering cache configuration, CSV normalisation, and test workflow.
- One-command `scripts/dev` bootstrap script.
- `hbc-cli` console utility for generating synthetic forecasts.
- Minimal Explorer page at `docs/index.html` for GitHub Pages.
- Colab/Binder badges to README for cloud execution.
- Draft release notes at `docs/releases/v0.1.0.md`.
- Jupyter notebook with synthetic data demo (`notebooks/demo.ipynb`).
- Unit tests and CI workflow for tests (`tests/` directory, `.github/workflows/test.yml`).
- Results folder with example CSVs (ground truth, forecasts, metrics) in `results/` directory.
- Python package structure with `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml`.
- FastAPI backend (`app/backend/`) and Next.js frontend (`app/frontend/`).
- Public data connectors for Wiki pageviews, OSM changesets, and FIRMS fires.
- Interactive diagram HTML page (`docs/interactive-diagram.html`).

### Changed
- FastAPI backend now normalises CSV columns, enforces cache eviction/TTL consistently, and keeps stub responses stable.
- Introduced a module shim so overrides of `RESULTS_DIR` / `MAX_CACHE_SIZE` stay in sync between `app.main` and the backend implementation.
- Shared synthetic forecast generator moved to `hbc.forecasting` for reuse across API and CLI.
- Switched Dockerfile to a multi-stage build that installs the package via `pyproject.toml`.

### Planned
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
