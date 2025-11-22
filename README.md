# The Convergence of Human-Behaviour Prediction
> Population-scale forecasting in a **zero-restriction** (*No-Guard-Rails*) data regime.

[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/render-diagram.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/codethor0/human-behaviour-convergence/badge)](https://securityscorecards.dev/viewer/?uri=github.com/codethor0/human-behaviour-convergence)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/codethor0/human-behaviour-convergence)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)
[![Tip](https://img.shields.io/badge/Tip-support-brightgreen)](https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01)
[![Monthly](https://img.shields.io/badge/Monthly-subscribe-blue)](https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00)

---

## What is this?

This project demonstrates **population-scale behavioural forecasting** using a three-layer architecture: 5.6B online training samples, 2.8B offline targets acquired via satellite & ground imagery, and 8.4B inference endpoints. The system combines centaur AI models, multi-modal fusion pipelines, and real-time prediction to forecast macro-behavioural states at unprecedented scale.

**Status:** Proof-of-concept (v0.1) — research artifact
**Paper:** Under review
**Data:** Synthetic sample (1% slice) available; full dataset under restricted access
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)

---

## Architecture Overview

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

## Who is this for?

- **Data science teams** exploring large-scale behavioural modelling
- **Public health agencies** interested in population-level forecasting
- **Researchers** studying AI alignment, privacy, and predictive systems
- **Policy analysts** evaluating implications of pervasive surveillance

## Quick Start

1. **Explore the diagram interactively:**
   [![Mermaid Live](https://img.shields.io/badge/Edit-Mermaid%20Live-orange?logo=mermaid)](https://mermaid.live/edit#pako:eNptkktvwjAMhf-KyhVapW2AbaQuTGySTQIkTpN2mrYpTeo0qfpxQvz3OV0YQ6VW9rPzsx379oL6oUdBD5yDAiVgNBzB0B8BqE7OaDbzOJt5NJt5tJj5tJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5)

2. **Run the demo notebook:**
   - Open `notebooks/demo.ipynb` in Jupyter Lab/Notebook
   - Or view online: *(coming soon: Binder/Colab badge)*

3. **Contribute:**
   See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

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
## Support

If this project helps you, consider supporting ongoing maintenance:

- **One-time tip:** https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01  
- **Monthly support:** https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00

**What you fund:** maintenance, docs, roadmap experiments, and new features.

Thank you!
