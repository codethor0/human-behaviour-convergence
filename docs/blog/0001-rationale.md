# Project Rationale: Why Human Behavior Convergence?

*November 2025*

We built Human Behavior Convergence to explore a simple question: can we study population-scale behavioral forecasting without touching real personal data? The short answer is yes—if you commit to an ethics-first mindset, synthetic pipelines, and radical transparency.

## What it is

Human Behavior Convergence is an open methodology for running large-scale behavioral forecasting experiments in a fully synthetic environment. It replicates the workflows of modern “centaur” prediction systems—hybrids where humans and machine learning models collaborate—while keeping every signal, cache, and forecast generated from deterministic seeds.

The project ships a FastAPI backend, a Next.js frontend shell, an interactive architecture diagram, and a set of Python utilities for generating synthetic forecasts. Our guiding principle is that anyone should be able to clone the repository, run `./scripts/dev`, and have the entire experiment running on their machine, complete with observability hooks and guardrails.

## Why synthetic data?

There is no shortage of privacy-sensitive behavior data in the world—location pings, social graphs, purchase histories. But accessing it ethically and legally is difficult, and publishing new tools that rely on real personal data often invites misuse. Instead of navigating that minefield, we created high-fidelity synthetic datasets that mirror the dynamics we care about (convergence, diffusion, feedback loops) without storing anything about real individuals. The synthetic corpus feeds both the backend API and the lab notebooks, so every forecast is reproducible and risk-free.

## Architecture: the three-layer stack

The repository centres on a three-layer architecture, visualised in the `diagram/` assets and the Explorer page:

1. **Train (online, 5.6B signals).** We simulate the constant stream of telemetry, clickstream, and wiki activity that modern models ingest. Each modality is generated using seeded noise fields, so running the pipeline twice yields identical inputs.
2. **Acquire (offline, 2.8B targets).** Not everyone is connected, so we mimic how organisations fall back to satellite imagery, IoT sensors, or manual surveys. These signals are slower but richer, and they let us test asynchronous ingestion paths.
3. **Process & Feedback (planetary scale).** At inference time, we fuse the modalities, run synthetic centaur models, and feed the outputs back into the simulated world. Because everything is deterministic, we can replay any scenario or swap out models while keeping the rest constant.

The static Explorer page (`docs/index.html`) brings these layers together: the diagram on the right, a forecast form on the left. When the API is live, the form posts to `/api/forecast` and displays the synthetic response; if the API is down, it automatically flips to a mocked result so you can keep exploring.

## Quickstart in two minutes

1. **Clone and bootstrap**
   ```bash
   git clone https://github.com/codethor0/human-behaviour-convergence.git
   cd human-behaviour-convergence
   ./scripts/dev
   ```
   The helper script creates a virtual environment, installs dependencies, runs `pytest`, launches `uvicorn app.main:app --port 8000`, and opens the Explorer page.

2. **Launch the Colab demo (optional)**
   Click the Colab badge in the README to open `notebooks/demo.ipynb`. Every cell uses the same synthetic seeds, so the results match what you see locally. When you’re ready to push changes, run `pre-commit run --all-files` and open a pull request.

## Ethical guardrails baked in

- **Synthetic-only outputs.** The API adds `"ethics": {"synthetic": true, "pii": false}` to every forecast response, a small reminder that we opted out of personal data entirely.
- **Deterministic seeding.** We lean on deterministic generators (`hbc.forecasting.generate_synthetic_forecast`) so that reviewers can reproduce any forecast just by passing the same region, horizon, and modalities.
- **Model & Data Card.** The repository includes a [model/data card](../model-data-card.md) that spells out purpose, limitations, non-goals, and misuse mitigations. It links directly to [ETHICS.md](../../ETHICS.md) and [SECURITY.md](../../SECURITY.md).
- **Cache observability.** `/api/cache/status` exposes hits, misses, and TTL configuration so you can inspect the system’s behavior without digging through logs.

## Three concrete use cases

1. **Public health rehearsal.** Suppose you need to evaluate how a synthetic flu outbreak might spread across regions. The Explorer can model region-specific horizons and modalities (mobility telemetry, satellite cues) to surface hotspots, all while staying in the synthetic sandbox.
2. **Mobility planning.** Transportation teams can simulate the impact of adding a new train line by tweaking synthetic mobility modalities and forecasting the behavioral uplift. Because everything is deterministic, policymakers can compare “before” and “after” scenarios in a controlled environment.
3. **Crisis simulation.** Emergency-response drills often require converging data from satellite imagery and IoT sensors. The synthetic Acquire layer lets you practice those ingestion paths, test cache eviction policies, and evaluate how quickly the centaur models converge, without touching real crisis data.

Each scenario reinforces the same point: we can prototype and review behavioral forecasting systems safely. When someone decides a real deployment is warranted, they already know where the pinch points and ethical questions reside.

## How to get involved

We seeded a set of “good first issues” and scripted onboarding because we want newcomers to have a path into the project. Recent additions include:

- `hbc-cli`: a console tool that mirrors the `/api/forecast` endpoint for quick experiments.
- `pyproject.toml`: packaging metadata so you can `pip install -e .` and depend on the utilities from other projects.
- A multi-stage Dockerfile to build minimal images for deployment.

You can help by trying the Explorer, opening bug reports, or drafting new synthetic scenarios. We also welcome pull requests that strengthen the documentation, extend the API, or refine the synthetic pipelines. Every contribution keeps the ethical bar high while making the toolkit more useful for the broader community.

## Closing thoughts

Human Behavior Convergence is our invitation to explore behavioral forecasting responsibly. By leaning on synthetic data, deterministic pipelines, and open collaboration, we can stress-test ideas that would otherwise stay locked inside proprietary systems. Whether you are a researcher, engineer, or policymaker, we hope this repository gives you a safe playground to build, critique, and improve the next generation of centaur forecasting systems.
