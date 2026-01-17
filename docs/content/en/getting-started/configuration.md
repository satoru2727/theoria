# Configuration

Theoria uses a layered configuration system:

1. **Environment variables** (highest priority)
2. **Project config** (`./config.theoria.yaml`)
3. **Global config** (`~/.config/theoria/config.yaml`)

## Configuration File

```yaml
# config.theoria.yaml
agent:
  provider: openai      # LLM provider
  model: gpt-4o         # Model name
  temperature: 0.7      # Response creativity (0.0-1.0)
  max_tokens: null      # Max response length (null = provider default)

bibliography:
  default_style: apa    # Citation style
  bib_file: references.bib

latex:
  compiler: pdflatex    # LaTeX compiler
  output_dir: build     # Build output directory

providers:
  openai:
    timeout: 120
  anthropic:
    timeout: 120
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `THEORIA_PROVIDER` | Override default provider |
| `THEORIA_MODEL` | Override default model |
| `THEORIA_TEMPERATURE` | Override temperature |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_API_KEY` | Google AI API key |

## Supported Providers

| Provider | Model Examples |
|----------|----------------|
| `openai` | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| `anthropic` | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` |
| `google` | `gemini-pro`, `gemini-1.5-pro` |
| `groq` | `llama3-70b-8192`, `mixtral-8x7b-32768` |
| `mistral` | `mistral-large-latest`, `mistral-medium` |
| `deepseek` | `deepseek-chat`, `deepseek-coder` |
| `ollama` | Any local model |

## Authentication Storage

API keys are stored in `~/.config/theoria/auth.json` with `600` permissions.

```bash
# Add API key
theoria auth add openai --key sk-...

# List configured providers
theoria auth list

# Check status
theoria auth status openai

# Remove
theoria auth remove openai
```

!!! note
    Environment variables always take precedence over stored keys.
