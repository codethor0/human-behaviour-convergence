# Good First Issue Drafts

These are pre-drafted issues you can copy into GitHub. Apply the labels `good first issue` and `help wanted` on creation.

---

## 1. Add Colab badge to README quick start

- **Summary:** Surface the existing Colab demo in the README sidebar so new visitors can launch the notebook instantly.
- **Tasks:**
  - Inject the Colab badge near the top TL;DR block.
  - Link to `notebooks/demo.ipynb`.
  - Mention that the notebook uses synthetic data only.
- **Acceptance criteria:** Badge renders correctly, markdown lint passes (`pre-commit run --all-files`).

## 2. Restructure architecture section into bullets + diagram link

- **Summary:** Convert the current architecture table into concise bullet points referencing the static + interactive diagrams.
- **Tasks:**
  - Replace the markdown table with bullet list.
  - Ensure both diagram links remain.
  - Keep existing narrative context.
- **Acceptance criteria:** README builds without broken links; bullets align with diagram content.

## 3. Create CLI usage example in docs

- **Summary:** Document `hbc-cli` usage with an example invocation.
- **Tasks:**
  - Add a snippet under a new "Command-line" subsection in README or docs.
  - Show sample JSON output.
  - Mention the deterministic synthetic nature.
- **Acceptance criteria:** Example works (`hbc-cli --region test --horizon 5`), snippet passes markdown lint.

## 4. Expand `/api/forecast` edge-case tests

- **Summary:** Add tests covering invalid modality payloads and horizon boundaries.
- **Tasks:**
  - Update `tests/test_api_backend.py` with cases for empty payload, horizon=1, horizon=30.
  - Assert 422 responses for invalid data (e.g., negative horizon).
- **Acceptance criteria:** `pytest tests/test_api_backend.py` passes and coverage unchanged or higher.

## 5. Seed three synthetic scenario JSONs and connect dropdown in Explorer

- **Summary:** Offer canned scenarios selectable in the Explorer UI.
- **Tasks:**
  - Add three JSON files under `results/scenarios/`.
  - Update `docs/index.html` to include a dropdown that auto-fills the form.
  - Ensure fallback/mocked mode still works.
- **Acceptance criteria:** Selecting a scenario updates the form fields; lint/tests pass.
