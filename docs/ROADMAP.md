# Roadmap

This document outlines the planned milestones and future development directions for the Human Behaviour Convergence project.

## Project Stewardship

Primary maintainer: **Thor Thor**  
Email: [codethor@gmail.com](mailto:codethor@gmail.com)  
LinkedIn: [https://www.linkedin.com/in/thor-thor0](https://www.linkedin.com/in/thor-thor0)

---

## Milestone 2: Transparency Drop

**Status:** Planned

**Goal:** Prove reproducibility on a public slice.

**Description:** This milestone focuses on making the forecasting pipeline fully reproducible and transparent by publishing public datasets and documentation.

### Tasks

- [ ] 100k synthetic row shard on Hugging Face datasets + DVC pointer
- [ ] DVC pipeline stage that reproduces the notebook end-to-end
- [ ] HTML report published to GitHub Pages (dvc metrics show --html)
- [ ] Model card (model-card.md) filled with limitations, ethical risks

**Related Issue:** [#8](https://github.com/codethor0/human-behaviour-convergence/issues/8)

---

## Milestone 3: Live Playground

**Status:** Planned

**Goal:** Give visitors an instant 'aha' moment.

**Description:** Create an interactive web-based playground that allows users to explore forecasts and test the system with their own data.

### Tasks

- [ ] Streamlit/Gradio app that loads the public shard and shows:
  - world map with predicted behavioural index slider
  - 'upload your CSV' adapter (accepts same schema)
- [ ] Host free on Hugging Face Spaces (zero infra cost)
- [ ] Embed screenshot + link at top of README → instant demo

**Related Issue:** [#9](https://github.com/codethor0/human-behaviour-convergence/issues/9)

---

## Milestone 4: Community Rails

**Status:** Planned

**Goal:** Turn energy into structured contributions.

**Description:** Establish community governance, contribution workflows, and regular engagement channels to support long-term project sustainability.

### Tasks

- [ ] all-contributors bot installed → auto-update README avatars
- [ ] RFC template + lightweight Technical Steering Committee (TSC) draft
- [ ] Monthly open Zoom call (calendar file + .ics in repo)
- [ ] 'good first issue' bot that labels PRs ≤20 lines

**Related Issue:** [#10](https://github.com/codethor0/human-behaviour-convergence/issues/10)

---

## Current Status

**Active Development:** v0.1 - transitioning from proof-of-concept to production-ready forecasting engine

**Focus Areas:**
- Core forecasting engine and API endpoints
- Public data connectors and ingestion pipelines
- Web dashboard for interactive exploration
- Documentation and reproducibility

For detailed feature planning, see [docs/app-plan.md](./app-plan.md).

