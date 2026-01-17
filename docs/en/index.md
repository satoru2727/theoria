# Theoria

**Humanities research & LaTeX drafting agentic CLI**

Theoria is a command-line tool that assists humanities researchers in clarifying arguments, managing citations, and editing LaTeX documents through AI-powered agents.

## Core Principles

- **Citation-first**: No claim without a traceable source
- **Approval-driven**: Agent proposes, human approves
- **Local-first**: Your data stays on your machine
- **Provider-agnostic**: Choose your LLM provider freely

## The Three Agents

| Agent | Role | Phase |
|-------|------|-------|
| **Theoretikos** | Socratic dialogue partner | Clarify → Challenge → Synthesize |
| **Bibliographos** | Literature search & citation | Search → Extract → Validate |
| **Graphos** | LaTeX editing assistant | Analyze → Edit → Repair |

## Quick Example

```bash
# Initialize project
theoria init

# Start Socratic dialogue
theoria chat

# Manage API keys
theoria auth add openai --key sk-...
```

## Tech Stack

- Python 3.11+
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [LiteLLM](https://github.com/BerriAI/litellm) - Provider abstraction
- [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) - CLI

## License

This is free and unencumbered software released into the public domain (WTFPL).
