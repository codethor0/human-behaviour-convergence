## Repo snapshot

This repository is small and documentation-focused. The single source of truth for the diagram is:

- `diagram/behaviour-convergence.mmd` — editable Mermaid source
- `diagram/behaviour-convergence.svg` and `diagram/behaviour-convergence.png` — generated assets (do not edit by hand)

The README states that CI automatically re-renders the SVG & PNG on every push. I did not find any agent-specific instruction files in the repo, so this file provides the minimal, actionable guidance an automated editing agent needs.

## Purpose for an AI coding agent

- Primary job: help author and refine the Mermaid diagram in `diagram/behaviour-convergence.mmd` and keep the repository documentation (README) in sync.
- Avoid editing generated files (`.svg`, `.png`) — change the `.mmd` and let CI regenerate images.

## Concrete behavior & rules

1. When making visual changes, edit only `diagram/behaviour-convergence.mmd`.
   - Example: to rename a node, update the text in the `.mmd` and commit.
2. Do not modify `diagram/behaviour-convergence.svg` or `diagram/behaviour-convergence.png` directly — these are build artifacts.
3. If updating README usage text, keep it short and reference the `.mmd` file and Mermaid Live for quick edits.

## Local verification (assumptions)

The README says CI re-renders images on push but no CI workflow was found in this repository tree. Two reasonable local checks an agent can suggest to a human contributor:

- Use Mermaid Live to edit and preview: https://mermaid.live — open `diagram/behaviour-convergence.mmd` and verify output.
- (Optional) If you want a local render, install the mermaid CLI (assumption) and run a command such as:

  ```bash
  # example (optional) — only if maintainer uses mermaid-cli
  npx @mermaid-js/mermaid-cli -i diagram/behaviour-convergence.mmd -o diagram/behaviour-convergence.svg
  ```

Note: mark the above as an assumption — the repo contains no package.json or workflow to confirm which tool is used in CI.

## Change examples (quick templates for commits)

- Small diagram tweak: "docs: update diagram node labels"
- Structural diagram change: "feat(diagram): add subsystem X to behavior convergence diagram"

Keep commit messages short and reference `diagram/behaviour-convergence.mmd` when applicable.

## When to open an issue / request human review

- If Mermaid syntax errors prevent CI render or local preview fails.
- If a proposed edit touches generated assets, ask for human confirmation and rationale.

## Files to inspect when debugging

- `README.md` — project intent and usage (primary doc)
- `diagram/behaviour-convergence.mmd` — authoritative diagram source

## Closing notes

This file is intentionally short and prescriptive: focus edits on the `.mmd` diagram source, avoid generated assets, and suggest local verification steps as optional assumptions. If you want, I can also add a GitHub Actions workflow that renders the Mermaid file automatically on push — tell me whether to add a specific renderer (e.g., `@mermaid-js/mermaid-cli`) and I'll scaffold it.
