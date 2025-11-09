# Behaviour Convergence Model & Data Card

## Purpose
- Provide a reproducible, synthetic testbed for population-scale behavioural forecasting.
- Evaluate centaur-style models (human + AI) across multimodal signals without exposing real individuals.
- Demonstrate observability, cache controls, and ethics-first instrumentation for public APIs.

## Data sources & generation
- **Synthetic core:** Scenario generator blends public statistical priors with handcrafted noise distributions.
- **Modalities:** satellite imagery embeddings, mobility telemetry, social/wiki events, environmental sensors—each simulated via deterministic seeds.
- **Temporal coverage:** daily horizons up to 30 days with replayable seeds (`hbc.forecasting` + `/api/forecast`).
- **Storage:** CSV artefacts in `results/` and canned scenarios (coming soon) for explorer dropdowns.

## Limitations
- Synthetic signals cannot predict real behaviour; they validate pipelines, not accuracy.
- No uncertainty calibration beyond handcrafted confidence scores.
- Does not model socio-economic or demographic attributes; region strings are free-text labels.

## Non-goals
- Deploying to production or making policy decisions.
- Collecting or inferring personal data.
- Benchmarking model accuracy on real-world datasets.

## Ethical constraints
- All outputs flagged as synthetic; the API returns `ethics = {synthetic: true, pii: false}`.
- Logs redact inputs and avoid storing raw payloads.
- See [ETHICS.md](../ETHICS.md) for privacy stance and research guardrails.

## Misuse mitigations
- Access limited to public synthetic endpoints; rate limiting enforced at API gateway (recommended for deployments).
- Automated tests prevent removal of ethics metadata and ensure deterministic seeding.
- Security guidance in [SECURITY.md](../SECURITY.md); report issues responsibly.

## Responsible release checklist
- Synthetic-only dataset (complete).
- Open API contract with ethical notes (complete).
- Documentation for quickstart + teardown (`scripts/dev`) (complete).
- Scenario fixtures for user studies (planned).
- External review of ethics documentation prior to real-data extension (planned).
