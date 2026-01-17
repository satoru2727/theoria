# Theoria Development Guidelines

## Project Overview

Theoria is a humanities research & LaTeX drafting agentic CLI tool.

- Language: Python 3.11+
- Agent Framework: LangGraph
- LLM Provider Abstraction: LiteLLM
- CLI Framework: Typer + Rich

## Architecture

```
src/theoria/
├── cli.py           # CLI entrypoint (Typer)
├── auth/            # Authentication (API keys, OAuth)
├── agents/          # LangGraph agents (Theoretikos, Bibliographos, Graphos)
├── providers/       # LLM provider abstraction via LiteLLM
├── bibliography/    # BibTeX management, citation tracking
├── latex/           # LaTeX editing, syntax repair
└── storage/         # SQLite storage for sessions, logs, citations
```

## Agents

| Agent | Role |
|-------|------|
| Theoretikos | Socratic dialogue, argument validation |
| Bibliographos | Literature search, citation extraction, BibTeX management |
| Graphos | LaTeX editing, syntax repair, structure maintenance |

## Key Principles

1. Citation-first: No claim without traceable source
2. Approval-driven: Agent proposes, human approves
3. Local-first: Data stays on user machine, only LLM calls go to cloud
4. Provider-agnostic: User chooses LLM provider freely

## Code Style

- Use `ruff` for linting and formatting
- Use `mypy --strict` for type checking
- All public functions must have type hints
- No docstrings unless absolutely necessary (complex algorithms, regex, etc.)
- Prefer self-documenting code over comments

## Commands

```bash
ruff check src tests
ruff format src tests
mypy src
pytest
```

## Config Locations

- Global: `~/.config/theoria/config.yaml`
- Auth: `~/.config/theoria/auth.json` (mode 600)
- Project: `./config.theoria.yaml`

Priority: env vars > project config > global config

## Auth Flow

1. API Key: `theoria auth add <provider> --key ...`
2. OAuth PKCE: `theoria auth login <provider>` (browser flow)
3. Device Code: `theoria auth login <provider> --device` (terminal flow)

## Testing

- Use pytest with pytest-asyncio
- Test files in `tests/` mirror `src/theoria/` structure
- Prefer integration tests over unit tests for agent behavior
