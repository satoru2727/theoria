# Theoria

Humanities research & LaTeX drafting agentic CLI.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: WTFPL](https://img.shields.io/badge/license-WTFPL-brightgreen.svg)](http://www.wtfpl.net/)

Theoria is an AI-powered command-line tool designed for humanities researchers. It combines Socratic dialogue, literature search, and LaTeX editing in a citation-first workflow.

## Features

- **Socratic Dialogue** (`theoria chat`) - Clarify and refine your arguments through dialectical examination
- **Literature Search** (`theoria search`) - Find academic sources and generate BibTeX entries
- **LaTeX Editing** (`theoria edit`) - AI-assisted LaTeX document editing with diff preview
- **Citation Management** (`theoria cite`) - Fuzzy search your bibliography and copy citations
- **Document Checking** (`theoria check`) - Verify label/ref integrity in LaTeX documents
- **Multi-provider Support** - Works with OpenAI, Anthropic, Google, Groq, Mistral, and more

## Installation

```bash
pip install theoria
```

Or with uv:

```bash
uv add theoria
```

## Quick Start

1. **Set up your API key:**

```bash
# Option 1: Environment variable
export OPENAI_API_KEY=your-key-here

# Option 2: Store in config
theoria auth add openai --key your-key-here
```

2. **Initialize a project:**

```bash
cd your-research-project
theoria init
```

3. **Start a dialogue:**

```bash
theoria chat
```

## Commands

| Command | Description |
|---------|-------------|
| `chat` | Socratic dialogue with Theoretikos agent |
| `search` | Literature search with Bibliographos agent |
| `edit <file>` | LaTeX editing with Graphos agent |
| `research` | Integrated research session (dialogue + search) |
| `cite <query>` | Search bibliography for citation keys |
| `check <file>` | Check LaTeX label/ref integrity |
| `compile <file>` | Compile LaTeX document |
| `init` | Initialize project config |
| `history` | View saved sessions |
| `export <id>` | Export session to Markdown |
| `auth add/remove/list/status/login` | Manage API authentication |

## Configuration

Theoria uses YAML configuration files:

- **Global:** `~/.config/theoria/config.yaml`
- **Project:** `./config.theoria.yaml` (overrides global)

Example configuration:

```yaml
agent:
  provider: openai
  model: gpt-4o
  temperature: 0.7
  max_tokens: 4096
```

## Supported Providers

- OpenAI (GPT-4, GPT-4o, etc.)
- Anthropic (Claude 3, etc.)
- Google (Gemini)
- Groq
- Mistral
- Cohere
- DeepSeek
- OpenRouter
- Ollama (local)

## Tech Stack

- Python 3.11+
- LangGraph (agent orchestration)
- LiteLLM (provider abstraction)
- Typer + Rich (CLI)
- pybtex (BibTeX parsing)
- aiosqlite (session storage)

## License

This is free and unencumbered software released into the public domain.

Do What The Fuck You Want To.
