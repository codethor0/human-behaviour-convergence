
# TL;DR
Population-scale forecasting is hard, especially with open synthetic data. This repo provides a transparent, extensible pipeline for behavioural prediction at scale—ready for contributors and new models.

**Problem:** Most population forecasting tools are closed, hard to extend, and lack reproducibility.
**Solution:** This project is open, modular, and ships with synthetic data and a plug-in architecture for predictors.

![Demo Screenshot](assets/demo.gif)


# TL;DR
Population-scale forecasting is hard, especially with open synthetic data. This repo provides a transparent, extensible pipeline for behavioural prediction at scale—ready for contributors and new models.

**Problem:** Most population forecasting tools are closed, hard to extend, and lack reproducibility.
**Solution:** This project is open, modular, and ships with synthetic data and a plug-in architecture for predictors.

![Demo Screenshot](assets/demo.gif)

> **We're building in the open!** Grab a Milestone-0 issue to appear in our all-contributors wall.

# The Convergence of Human-Behaviour Prediction
> Population-scale forecasting in a **zero-restriction** (*No-Guard-Rails*) data regime.

[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/render-diagram.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/codethor0/human-behaviour-convergence/badge)](https://securityscorecards.dev/viewer/?uri=github.com/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)

---

## What is this?

This project demonstrates **population-scale behavioural forecasting** using a three-layer architecture: 5.6B online training samples, 2.8B offline targets acquired via satellite & ground imagery, and 8.4B inference endpoints. The system combines centaur AI models, multi-modal fusion pipelines, and real-time prediction to forecast macro-behavioural states at unprecedented scale.

**Status:** Proof-of-concept (v0.1) — research artifact
**Paper:** Under review
**Data:** Synthetic sample (1% slice) available; full dataset under restricted access
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)

---

## Interactive Architecture

**[Explore the Interactive Diagram →](https://codethor0.github.io/human-behaviour-convergence/docs/interactive-diagram.html)**

Click, zoom, and explore the full system architecture with interactive tooltips and real-time rendering. The diagram shows how 8.4 billion individuals converge into a unified predictive system.

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



# The Convergence of Human-Behaviour Prediction
> Population-scale forecasting in a **zero-restriction** (*No-Guard-Rails*) data regime.

[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/render-diagram.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/codethor0/human-behaviour-convergence/badge)](https://securityscorecards.dev/viewer/?uri=github.com/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)

---

## What is this?

This project demonstrates **population-scale behavioural forecasting** using a three-layer architecture: 5.6B online training samples, 2.8B offline targets acquired via satellite & ground imagery, and 8.4B inference endpoints. The system combines centaur AI models, multi-modal fusion pipelines, and real-time prediction to forecast macro-behavioural states at unprecedented scale.

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
- Preview/edit in your browser via Mermaid Live: https://mermaid.live
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

- **Data science teams** exploring large-scale behavioural modelling
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

[![Open in Colab](https://colab.research.googleusercontent.com/assets/colab-badge.svg)](https://colab.research.google.com/github/codethor0/human-behaviour-convergence/blob/master/notebooks/demo.ipynb)
[![Launch Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/codethor0/human-behaviour-convergence/HEAD?labpath=notebooks%2Fdemo.ipynb)

1. Click a badge above.
2. Execute the notebook to reproduce the synthetic pipeline without local setup.

## Responsible Disclosure

If you discover a security or privacy issue (including ethical concerns about the model or data), please report it responsibly:

- **Security issues:** Open a confidential issue or email the maintainer (see [SECURITY.md](./SECURITY.md))
- **Ethical concerns:** See [ETHICS.md](./ETHICS.md) for our approach to privacy, IRB compliance, and misuse mitigation

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

We are building **Behaviour Convergence Explorer**, an interactive web application that surfaces the forecasting pipeline, synthetic results, and ethical guardrails.

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
  title = {Human Behaviour Convergence: Population-Scale Forecasting},
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
