[![Tip](https://img.shields.io/badge/Tip-support-brightgreen)](https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01)
[![Monthly](https://img.shields.io/badge/Monthly-subscribe-blue)](https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00)

# Support my open-source work

If these projects help you, consider supporting ongoing maintenance:

- One-time tip: https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01
- Monthly support: https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00

**What you fund:** maintenance, docs, roadmap experiments, and new features.

Thank you!

# TL;DR
Population-scale forecasting is hard, especially with open synthetic data. This repo provides a transparent, extensible pipeline for behavioral prediction at scale—ready for contributors and new models.

**Problem:** Most population forecasting tools are closed, hard to extend, and lack reproducibility.
**Solution:** This project is open, modular, and ships with synthetic data and a plug-in architecture for predictors.

![Demo Screenshot](assets/demo.gif)

> **We're building in the open!** Grab a Milestone-0 issue to appear in our all-contributors wall.

<div align="center">

# Behavior Convergence Explorer

[![Tests](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/test.yml)
[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/codethor0/human-behaviour-convergence?logo=codecov)](https://app.codecov.io/gh/codethor0/human-behaviour-convergence)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg?logo=python)](https://www.python.org/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/codethor0/human-behaviour-convergence/badge?style=flat)](https://securityscorecards.dev/viewer/?uri=github.com/codethor0/human-behaviour-convergence)
[![DOI](https://img.shields.io/badge/DOI-soon-lightgrey.svg)](https://zenodo.org/)

<p><em>Ethics-first, synthetic-only behavioral forecasting. No personal data—ever.</em></p>

</div>

---

## What is this?

This project demonstrates **population-scale behavioral forecasting** using a three-layer architecture: 5.6B online training samples, 2.8B offline targets acquired via satellite & ground imagery, and 8.4B inference endpoints. The system combines centaur AI models, multi-modal fusion pipelines, and real-time prediction to forecast macro-behavioral states at unprecedented scale.

**Status:** Proof-of-concept (v0.1) — research artifact
**Paper:** Under review
**Data:** Synthetic sample (1% slice) available; full dataset under restricted access
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)

---

## Interactive Architecture

**[Explore the Interactive Diagram →](https://codethor0.github.io/human-behaviour-convergence/docs/interactive-diagram.html)**

Click, zoom, and explore the full system architecture with interactive tooltips and real-time rendering. The diagram shows how 8.4 billion individuals converge into a unified predictive system.

<p align="center">
  <a href="https://codethor0.github.io/human-behaviour-convergence/docs/interactive-diagram.html" target="_blank" rel="noreferrer">
    <img src="https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg" alt="Human Behavior Convergence live architecture diagram preview" width="100%" />
  </a><br />
  <em>Hover, pan, zoom, and follow animated edges in the live view</em>
</p>

### Features
- **Interactive nodes** - Click to highlight components and data flows
- **Zoom & Pan** - Navigate the complete architecture at any scale
- **Live editing** - Modify the diagram source and see changes instantly
- **Dark theme** - Optimized for readability and visual impact

<details>
<summary>View static diagram (fallback)</summary>

![diagram](diagram/behaviour-convergence.svg)

</details>

### Architecture Components

| Layer | Scale | Description |
|-------|-------|-------------|
| **TRAIN** | 5.6B online | Digital natives generating clickstream, geolocation, and telemetry data |
| **ACQUIRE** | 2.8B offline | Limited-connectivity populations via orbital imaging and ground networks |
| **PROCESS** | 8.4B total | Real-time fusion and inference across planetary scale compute fabric |
| **FEEDBACK** | Continuous | Predictive outputs enable targeted interventions generating new training data |



# The Convergence of Human-Behavior Prediction
> Population-scale forecasting in a **zero-restriction** (*No-Guard-Rails*) data regime.

[![Render Diagram](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/render-diagram.yml/badge.svg?branch=main)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/render-diagram.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/codethor0/human-behaviour-convergence/badge?style=flat)](https://securityscorecards.dev/viewer/?uri=github.com/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)

---

## What is this?

This project demonstrates **population-scale behavioral forecasting** using a three-layer architecture: 5.6B online training samples, 2.8B offline targets acquired via satellite & ground imagery, and 8.4B inference endpoints. The system combines centaur AI models, multi-modal fusion pipelines, and real-time prediction to forecast macro-behavioral states at unprecedented scale.

**Status:** Proof-of-concept (v0.1) — research artifact
**Paper:** Under review
**Data:** Synthetic sample (1% slice) available; full dataset under restricted access
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)

---

## Architecture Overview

- View the interactive diagram (editable): [Interactive Diagram](docs/interactive-diagram.html)
- Static fallback:

![diagram](diagram/behaviour-convergence.svg)

## What's inside
| File | Purpose |
|------|---------|
| `diagram/behaviour-convergence.mmd` | Source Mermaid diagram – edit here |
| `diagram/behaviour-convergence.svg` | Auto-generated vector (perfect for docs / slides) |
| `diagram/behaviour-convergence.png` | Hi-res PNG (2400 px) – social cards, posters |
| `notebooks/` | Jupyter notebooks with end-to-end demos |
| `results/` | Ground truth, forecasts, and error metrics (CSV) |
| `tests/` | Unit tests and CI validation |

## Diagram quickstart

- Edit the source: `diagram/behaviour-convergence.mmd` (don’t edit `.svg/.png`).
- Preview/edit in your browser via Mermaid Live (preloaded with this diagram): https://mermaid.live/edit#url=https://raw.githubusercontent.com/codethor0/human-behaviour-convergence/main/diagram/behaviour-convergence.mmd


- CI behavior:
  - Pull requests: renders to a temporary location to validate Mermaid syntax (no commits).
  - Pushes: renders `svg/png` and opens an automated PR only when outputs actually change.

### Optional: local render

If you prefer a local preview without relying on CI or Mermaid Live, you can use the Mermaid CLI (optional):

```bash
# install once (global)
npm install -g @mermaid-js/mermaid-cli

# render SVG and PNG locally
mmdc -i diagram/behaviour-convergence.mmd -o diagram/behaviour-convergence.svg
mmdc -i diagram/behaviour-convergence.mmd -o diagram/behaviour-convergence.png -b transparent -s 2
```

## Who is this for?

- **Data science teams** exploring large-scale behavioral modeling
- **Public health agencies** interested in population-level forecasting
- **Researchers** studying AI alignment, privacy, and predictive systems
- **Policy analysts** evaluating implications of pervasive surveillance

## Quick Start

1. **Bootstrap locally**
   ```bash
   git clone https://github.com/codethor0/human-behaviour-convergence.git
   cd human-behaviour-convergence
   ./scripts/dev
   ```
   The helper script creates `.venv`, installs dependencies, runs `pytest`, launches `uvicorn app.main:app --port 8000`, and opens the static Explorer page.

2. **Explore**
   - API: http://localhost:8000/docs (interactive OpenAPI + ReDoc)
   - Explorer: open `docs/index.html` (falls back to mocked responses if the API is offline)

3. **Contribute**
   - Check [CONTRIBUTING.md](./CONTRIBUTING.md) for pre-commit hooks, coding style, and roadmap issues.

## Run in the cloud

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/codethor0/human-behaviour-convergence/blob/master/notebooks/demo.ipynb)
[![Launch Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/codethor0/human-behaviour-convergence/HEAD?labpath=notebooks%2Fdemo.ipynb)

1. Click a badge above.
2. Execute the notebook to reproduce the synthetic pipeline without local setup.

## Architecture at a glance

- **Train (online, 5.6B signals):** synthetic clickstream, telemetry, and wiki activity.
- **Acquire (offline, 2.8B targets):** orbital imagery + ground IoT filling gaps.
- **Process (planetary scale):** centaur models fuse multimodal features; feedback loop closes the simulation.
- Explore the full diagram at [`diagram/behaviour-convergence.svg`](diagram/behaviour-convergence.svg) or the interactive version in [`docs/interactive-diagram.html`](docs/interactive-diagram.html).

## Contributing (quick steps)

1. `git clone` and `./scripts/dev` (creates `.venv`, installs deps, runs tests, launches API + Explorer).
2. Make your change; run `pytest` and `pre-commit run --all-files` before committing.
3. Open a PR referencing an issue (or create one). We label starter work with `good first issue` and `help wanted`.

## Run CI Locally

Reproduce CI checks locally before pushing:

```bash
# Install all dependencies
pip install -r app/backend/requirements.txt
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install black mypy ruff semgrep pytest-cov

# Run linting
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402

# Check formatting
black --check app/backend tests hbc

# Type checking (non-blocking)
mypy --strict app/backend tests hbc || true

# Security scan
semgrep --config=auto app/backend tests hbc

# Run tests with coverage
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v

# Run all checks (matches CI)
./scripts/dev test
```

### Docker-based CI Reproduction

```bash
# Build the Docker image
docker build -t hbc-test .

# Run tests in container (matches CI environment)
docker run --rm hbc-test sh -c "pip install -r requirements-dev.txt && pytest tests/ -v"

# Run specific CI checks
docker run --rm hbc-test sh -c "pip install -r requirements-dev.txt black ruff && black --check app/backend tests hbc"
docker run --rm hbc-test sh -c "pip install -r requirements-dev.txt ruff && ruff check app/backend tests hbc"
```

### CI Matrix Jobs

The test workflow runs on Python 3.10, 3.11, and 3.12. To test a specific version:

```bash
# Using pyenv (recommended)
pyenv install 3.10.19
pyenv install 3.11.7
pyenv install 3.12.1
pyenv local 3.10.19  # Test with Python 3.10
pytest tests/ -v

# Using Docker
docker run --rm -v $(pwd):/app -w /app python:3.10 pip install -r requirements-dev.txt && pytest tests/ -v
docker run --rm -v $(pwd):/app -w /app python:3.11 pip install -r requirements-dev.txt && pytest tests/ -v
docker run --rm -v $(pwd):/app -w /app python:3.12 pip install -r requirements-dev.txt && pytest tests/ -v
```

### Environment Variables

CI uses these environment variables (set automatically in GitHub Actions):
- `CI=true` - Enables network-dependent tests
- `PYTHON_VERSION` - Python version from matrix (3.10, 3.11, 3.12)
- `DISK_CAP_GB=10` - Maximum disk usage in GB (enforced in all workflows)
- `MAX_LOG_MB=5` - Maximum log file size in MB (logs are trimmed if exceeded)

### CI Configuration

#### Cache Strategy
- **Pip Cache**: Keyed by OS + Python version + lockfile checksums
  - Cache keys: Automatically generated by `actions/setup-python@v6` with `cache: 'pip'`
  - Cache dependency paths: `requirements.txt`, `requirements-dev.txt`, `app/backend/requirements.txt`
  - Restore keys allow minor version drift
- **NPM Cache**: Keyed by OS + Node version + package-lock.json hash
  - Cache keys: Automatically generated by `actions/setup-node@v6` with `cache: 'npm'`
  - Cache dependency path: `app/frontend/package-lock.json`

#### Parallelism
- **Test Execution**: `pytest-xdist` with `-n auto` (uses all available CPUs)
- **Workflow Jobs**: Parallel execution of lint, type-check, security-scan, test, sbom-scan
- **Matrix Jobs**: Python 3.10, 3.11, 3.12 run in parallel with `fail-fast: false`

#### Path Filters
Workflows run only when relevant files change:
- `**.py` - Python source files
- `tests/**` - Test files
- `requirements*.txt` - Dependency files
- `pyproject.toml` - Project configuration
- Workflow-specific paths (e.g., `app/**` for app-ci.yml)

#### Disk Hygiene
- **Pre-cleanup**: Removes Python cache (`__pycache__`, `.pyc`) before each job
- **Post-cleanup**: Removes test artifacts (`.pytest_cache`, `htmlcov`) after tests
- **Disk Cap**: Enforced at 10GB per job (configurable via `DISK_CAP_GB`)
- **Log Trimming**: Logs larger than 5MB are trimmed (configurable via `MAX_LOG_MB`)
- **Artifact Retention**: 30 days for PR artifacts, 90 days for release artifacts

#### Concurrency Controls
- **Cancel in-progress**: PR updates cancel previous runs to reduce queue time
- **Concurrency groups**: `${{ github.workflow }}-${{ github.ref }}`
- **Fail-fast**: Disabled for matrix jobs to see all failures

#### Maintenance
- **Weekly cleanup**: Runs every Sunday at 00:00 UTC
- **Metrics report**: Tracks workflow runs, cache status, artifact status
- **Manual trigger**: Can be triggered via `workflow_dispatch`

## Public data snapshots (daily)

Use the CLI to download and apply the latest public inputs:

```bash
# Pull yesterday's data and update data/public/latest
poetry run hbc-cli sync-public-data --apply --summary

# Fetch a specific day and keep the files only
poetry run hbc-cli sync-public-data --date 2025-11-09 --sources wiki osm
```

Snapshots are written to `data/public/<date>/` with a manifest at
`data/public/latest/snapshot.json`. Set `FIRMS_MAP_KEY` in your environment to enable the NASA
FIRMS connector; otherwise it returns an empty placeholder.

## Conventions

- American English spelling throughout docs, UI copy, and comments (`behavior`, `behavioral`). Legacy identifiers and URLs keep their original repo slug spelling for compatibility.

## Responsible Disclosure

If you discover a security or privacy issue (including ethical concerns about the model or data), please report it responsibly:

- **Security issues:** Open a confidential issue or email the maintainer (see [SECURITY.md](./SECURITY.md))
- **Ethical concerns:** See [ETHICS.md](./ETHICS.md) for our approach to privacy, IRB compliance, and misuse mitigation
- **Synthetic scope:** Review the [Model & Data Card](docs/model-data-card.md) for details on the generation pipeline, limitations, and mitigations.

## Development

- **Prerequisites:** Python 3.10+, Node 20 (for diagram rendering)
- **Setup:**
  ```bash
  git clone https://github.com/codethor0/human-behaviour-convergence.git
  cd human-behaviour-convergence
  pip install -r requirements.txt
  pip install -r requirements-dev.txt  # for testing
  ```
- **Run tests:**
  ```bash
  pytest tests/ --cov
  ```

## Application Roadmap

We are building **Behavior Convergence Explorer**, an interactive web application that surfaces the forecasting pipeline, synthetic results, and ethical guardrails.

- Architecture & feature plan: [docs/app-plan.md](./docs/app-plan.md)
- Current milestone: `app-v0.1` — scaffold Next.js + FastAPI workspace, CI, and interactive diagram
- Tech stack preview: Next.js (TypeScript), Tailwind, FastAPI, Pandas, Vercel/Render
- Principles: synthetic data only, transparent ethics, extensible APIs

Contributions welcome! Open an issue with the label `app` to collaborate on frontend, backend, or UX tasks.

## Citation

If you use this project in your research, please cite:

```bibtex
@software{human_behaviour_convergence,
  author = {codethor0},
  title = {Human Behavior Convergence: Population-Scale Forecasting},
  year = {2025},
  url = {https://github.com/codethor0/human-behaviour-convergence}
}
```

See [CITATION.cff](./CITATION.cff) for machine-readable metadata.

## Enable Pages
To publish the rendered SVG as a static page, enable GitHub Pages in your repo settings: Settings → Pages → Deploy from a branch → Branch: `master` / (root). After a successful deploy the diagram will be available at:

`https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg`

---

## License

MIT

## Updates & Announcements

- *Nov 2025:* [Project rationale blog post](docs/blog/0001-rationale.md) — why we built this synthetic, ethics-first explorer.
- *Nov 2025:* [Repository polish checklist](docs/repo-polish.md) — description, topics, and social preview steps for GitHub settings.
- *Upcoming:* [Release notes draft for v0.1.0](docs/releases/v0.1.0.md) — update date & DOI at release time.
