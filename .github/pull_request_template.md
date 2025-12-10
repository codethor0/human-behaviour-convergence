# Pull Request

## Description
<!-- Describe your changes clearly and concisely -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
<!-- REQUIRED: Confirm that you have run tests locally -->

- [ ] I have run `pytest tests/` locally and all tests pass
- [ ] I have verified that `ruff check app/ tests/ scripts/` passes
- [ ] I have verified that `black --check app/ tests/ scripts/` passes
- [ ] I have checked that no new temporary/debug files were added
- [ ] I have verified imports work correctly with `PYTHONPATH=$PWD python -c "import app"`
- [ ] I have run `.github/scripts/validate_repo_health.py` and it passes
- [ ] I have verified that all workflow YAML files are valid
- [ ] I have checked that no new environment variables are required (or documented them)
- [ ] I have verified test discovery works: `pytest --collect-only tests/`

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Environment Variables
<!-- If this PR requires new environment variables, document them here -->
- [ ] No new environment variables required
- [ ] New environment variables documented in `docs/ENVIRONMENT_VARIABLES.md`

## Breaking Changes
<!-- If this PR includes breaking changes, describe them here -->
- [ ] No breaking changes
- [ ] Breaking changes documented in CHANGELOG.md

## Additional Notes
<!-- Add any additional context or notes here -->
