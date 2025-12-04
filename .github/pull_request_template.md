# Pull Request

## Description
<!-- Describe your changes here -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Workflow/CI change
- [ ] Other (please describe)

## Testing
- [ ] I have run the test suite locally: `pytest tests/`
- [ ] I have verified linting passes: `ruff check app/ tests/ scripts/` and `black --check app/ tests/ scripts/`
- [ ] I have verified the build works: `python -c "import app"`
- [ ] All existing tests pass
- [ ] New tests have been added for new functionality

## Checklist
- [ ] Code follows the project's style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated (if applicable)
- [ ] No new warnings introduced
- [ ] No temporary/debug files committed
- [ ] All workflow paths validated (if workflow changes)

## Workflow Changes (if applicable)
If this PR modifies `.github/workflows/`:
- [ ] YAML syntax validated
- [ ] All referenced paths exist
- [ ] Python/Node versions are correct
- [ ] Permissions are appropriate
- [ ] Tested locally (if possible)

## Environment Variables (if applicable)
- [ ] New environment variables documented in `docs/ENVIRONMENT_VARIABLES.md`
- [ ] Default values provided for CI
- [ ] No secrets committed

## Breaking Changes (if applicable)
- [ ] Breaking changes documented
- [ ] Migration guide provided (if needed)
