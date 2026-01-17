# Contributing

## Development Setup

```bash
git clone https://github.com/theoria-project/theoria.git
cd theoria
pip install -e ".[dev]"
```

## Code Quality

### Lint & Format

```bash
ruff check src tests
ruff format src tests
```

### Type Check

```bash
mypy src
```

### Test

```bash
pytest
```

## Code Style

- **ruff** for linting and formatting (line-length 100, py311 target)
- **mypy --strict** for type checking
- All public functions require type hints
- No docstrings unless absolutely necessary
- Prefer self-documenting code over comments

## Anti-Patterns

Avoid these:

- `# type: ignore` or `cast(Any, ...)` without justification
- Empty exception handlers (`except: pass`)
- Hardcoded provider keys
- Docstrings for simple, obvious functions

## Project Conventions

### Config Priority

```
env vars > ./config.theoria.yaml > ~/.config/theoria/config.yaml
```

### Adding a New Agent

1. Create `src/theoria/agents/your_agent.py`
2. Define `YourState(TypedDict)` with phase tracking
3. Implement `StateGraph` with nodes and routing
4. Add streaming support via `stream_*` method

### Adding a CLI Command

```python
# In cli.py
@app.command()
def your_command(
    option: Annotated[str, typer.Option("--option", "-o", help="Description")] = "default",
) -> None:
    """Command description."""
    ...
```

## Pull Requests

1. Fork and create a feature branch
2. Ensure all checks pass (`ruff`, `mypy`, `pytest`)
3. Write clear commit messages
4. Submit PR with description of changes

## License

By contributing, you agree that your contributions will be released under the WTFPL license.
