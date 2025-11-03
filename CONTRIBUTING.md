# Contributing

Thanks for your interest in improving this project!

## Quickstart
- The diagram’s source of truth is `diagram/behaviour-convergence.mmd`.
- Preview and edit via Mermaid Live: https://mermaid.live
- On merge to `main`, CI re-renders `diagram/behaviour-convergence.svg` and `.png` via GitHub Actions.

## Making changes
1. Fork and create a branch.
2. Edit `diagram/behaviour-convergence.mmd` only. Do not edit generated `.svg`/`.png` by hand.
3. If you add nodes/edges, keep labels concise and wrap long text with `\n` for readability.
4. Open a Pull Request. The render workflow will attach updated artifacts if they change.

## Commit style
- Use concise, descriptive commits. Conventional Commits are welcome, e.g., `feat(diagram): add feedback loop` or `docs(readme): clarify Pages URL`.

## Development notes
- Local render (optional):
  - Assumption: using `@mermaid-js/mermaid-cli`.
  - Example:
    - `npx @mermaid-js/mermaid-cli -i diagram/behaviour-convergence.mmd -o diagram/behaviour-convergence.svg`

## Code of Conduct
By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).
