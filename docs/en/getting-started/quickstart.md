# Quick Start

## 1. Set Up Authentication

Theoria needs an API key from an LLM provider. Choose one:

=== "OpenAI"
    ```bash
    theoria auth add openai --key sk-your-api-key
    ```

=== "Anthropic"
    ```bash
    theoria auth add anthropic --key sk-ant-your-api-key
    ```

=== "Environment Variable"
    ```bash
    export OPENAI_API_KEY=sk-your-api-key
    ```

## 2. Initialize Your Project

```bash
cd your-research-project
theoria init
```

This creates `config.theoria.yaml` with default settings.

## 3. Start a Dialogue

```bash
theoria chat
```

You'll enter an interactive session with **Theoretikos**, your Socratic dialogue partner.

### Example Session

```
You: Thesis: Social media has fundamentally changed political discourse

Theoretikos: An interesting thesis. Let me help you examine it more closely.

When you say "fundamentally changed," what specific transformation do you 
have in mind? Are we talking about:
1. The speed of information spread?
2. The democratization of voice?
3. The nature of argumentation itself?

Also, could you clarify your temporal scope? Changed compared to when?
```

## 4. Use Slash Commands

During a chat session:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/save` | Save current session |
| `/status` | Show dialogue state |
| `/clear` | Reset conversation |
| `/exit` | Exit chat |

## 5. Resume a Session

```bash
# List saved sessions
theoria history

# Resume by ID
theoria chat --session ses_abc123def456
```

## Next Steps

- [Configuration](configuration.md) - Customize your setup
- [Theoretikos](../agents/theoretikos.md) - Learn about Socratic dialogue
