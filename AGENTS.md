# Theoria Development Guidelines

**Generated:** 2026-01-18
**Commit:** 04469c4
**Branch:** main

## Overview

Humanities research & LaTeX drafting agentic CLI. Python 3.11+ / LangGraph / LiteLLM / Typer + Rich.

## Structure

```
src/theoria/
├── cli.py              # Entry point - Typer app, auth subcommands
├── agents/             # LangGraph agents (Theoretikos, Bibliographos, Graphos)
│   ├── theoretikos.py  # Socratic dialogue - StateGraph with clarify/challenge/synthesize
│   ├── bibliographos.py# Literature search, citation extraction
│   └── graphos.py      # LaTeX editing, syntax repair
├── auth/               # API key & OAuth storage
│   ├── store.py        # JSON file storage (~/.config/theoria/auth.json)
│   └── oauth.py        # PKCE/device code flows
├── config/             # Pydantic settings, YAML loader
│   └── loader.py       # Config priority: env > project > global
├── providers/          # LiteLLM wrapper (LLMClient, Message)
├── bibliography/       # BibTeX management
├── latex/              # LaTeX editing utilities
└── storage/            # SQLite for sessions, logs
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Add CLI command | `cli.py` | Use `@app.command()` decorator |
| Add auth subcommand | `cli.py` | Use `@auth_app.command()` |
| New agent | `agents/` | Subclass pattern from theoretikos.py |
| LLM call | `providers/__init__.py` | Use `LLMClient.complete()` or `.stream()` |
| Config option | `config/loader.py` | Add to appropriate Pydantic model |
| API key env var | `auth/store.py` | Add to `env_map` in `get_api_key_from_env()` |

## Agent Architecture

All agents use LangGraph StateGraph pattern:
```python
class AgentState(TypedDict, total=False):
    messages: list[Message]
    phase: Literal[...]
    # domain-specific fields

class Agent:
    def __init__(self, config: Config | None = None):
        self.client = LLMClient(config)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph[AgentState]:
        # add_node, add_conditional_edges, set_entry_point
```

## Key Principles

1. **Citation-first**: No claim without traceable source
2. **Approval-driven**: Agent proposes, human approves
3. **Local-first**: Data stays on user machine, only LLM calls go to cloud
4. **Provider-agnostic**: User chooses LLM provider freely via LiteLLM

## Conventions

- `ruff` for lint/format (line-length 100, py311 target)
- `mypy --strict` for type checking
- All public functions: type hints required
- No docstrings unless absolutely necessary (complex algorithms, regex)
- Prefer self-documenting code over comments
- Config priority: env vars > `./config.theoria.yaml` > `~/.config/theoria/config.yaml`

## Anti-Patterns

- **No `as any` / `@ts-ignore` equivalents**: Never suppress mypy errors
- **No empty exception handlers**: Always handle or re-raise
- **No docstrings for simple functions**: Code should be self-documenting
- **No hardcoded provider keys**: Use `auth/store.py` or env vars

## Commands

```bash
# Lint & format
ruff check src tests
ruff format src tests

# Type check
mypy src

# Test
pytest

# Run CLI
theoria --help
theoria auth add openai --key ...
theoria chat
```

## Auth Flow

1. **API Key**: `theoria auth add <provider> --key ...`
2. **OAuth PKCE**: `theoria auth login <provider>` (browser flow)
3. **Device Code**: `theoria auth login <provider> --device` (terminal flow)

Env var overrides stored auth. Mapping in `auth/store.py:env_map`.

## Config Locations

| Type | Path | Mode |
|------|------|------|
| Global | `~/.config/theoria/config.yaml` | 644 |
| Auth | `~/.config/theoria/auth.json` | 600 |
| Project | `./config.theoria.yaml` | 644 |

## Testing

- pytest with pytest-asyncio (asyncio_mode = "auto")
- Test files mirror `src/theoria/` structure
- Prefer integration tests over unit tests for agent behavior
- Use `CliRunner` from typer.testing for CLI tests

## Roadmap

See **[TODO.md](./TODO.md)** for the production roadmap.

Current priority: **Phase 1 (Core CLI Experience)** - making `chat` command functional.

## Documentation

User-facing documentation is in `docs/` using MkDocs Material with i18n support.

**IMPORTANT**: Update documentation alongside code changes. When adding/modifying features:

1. Update relevant English docs in `docs/en/`
2. Update corresponding Japanese docs in `docs/ja/`
3. Keep both languages in sync

```bash
# Preview docs locally
uv run mkdocs serve

# Build static site
uv run mkdocs build
```

| Task | Location |
|------|----------|
| Add CLI command docs | `docs/{en,ja}/cli.md` |
| Add agent docs | `docs/{en,ja}/agents/` |
| Update architecture | `docs/{en,ja}/architecture.md` |
| Update getting started | `docs/{en,ja}/getting-started/` |

## Notes

- LiteLLM/LangGraph imports: `ignore_missing_imports = true` in mypy
- SQLite storage in `storage/` - not yet implemented
- OAuth flows in `auth/oauth.py` - CLI integration pending
