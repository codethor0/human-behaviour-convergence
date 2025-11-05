# Extending Behaviour Convergence: Predictor Plugins

This project supports plug-in predictors for behavioural forecasting. You can add your own model by creating a Python class and registering it as an entry point.

## Quickstart

1. **Create a predictor class:**
   - Example: `predictors/example_predictor.py`
   ```python
   class ExamplePredictor:
       def predict(self, data):
           # Your prediction logic here
           return data
   ```
2. **Register your plugin:**
   - Add an entry point in your `setup.py` or `pyproject.toml`:
   ```toml
   [project.entry-points.human_behaviour_predictor]
   example = "predictors.example_predictor:ExamplePredictor"
   ```
3. **Discover plugins:**
   - Use the registry:
   ```python
   from predictors.registry import registry
   print(registry.list_predictors())
   predictor = registry.get_predictor("example")
   result = predictor().predict(data)
   ```

## Template Repo
- See: [human-behaviour-predictor-template](https://github.com/codethor0/human-behaviour-predictor-template)

## Contribute a Predictor
- Fork this repo or use the template
- Add your predictor class and entry point
- Open a PR with your plugin

## Community Label
- Issues and PRs for predictors use the `community` label

---

For more, see the [docs](./app-plan.md) and roadmap milestones.
