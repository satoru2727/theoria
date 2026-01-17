# CLI Reference

## Global Options

```bash
theoria --help
```

## Commands

### `theoria version`

Display the current version.

```bash
theoria version
# theoria 0.1.0
```

### `theoria init`

Initialize a new Theoria project in the current directory.

```bash
theoria init [--force]
```

| Option | Description |
|--------|-------------|
| `--force, -f` | Overwrite existing config file |

Creates `config.theoria.yaml` and detects existing `.bib` and `.tex` files.

### `theoria chat`

Start an interactive dialogue session with Theoretikos.

```bash
theoria chat [--session SESSION_ID]
```

| Option | Description |
|--------|-------------|
| `--session, -s` | Resume a saved session by ID |

#### Slash Commands

| Command | Description |
|---------|-------------|
| `/help`, `/?` | Show available commands |
| `/exit`, `/quit`, `/q` | Exit chat |
| `/clear`, `/reset` | Clear conversation history |
| `/save` | Save session to disk |
| `/status` | Show current dialogue state |

### `theoria history`

List saved chat sessions.

```bash
theoria history [--limit N]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Maximum sessions to show (default: 20) |

## Auth Subcommands

### `theoria auth add`

Add an API key for a provider.

```bash
theoria auth add PROVIDER --key KEY
```

The key will be prompted securely if not provided.

### `theoria auth remove`

Remove authentication for a provider.

```bash
theoria auth remove PROVIDER
```

### `theoria auth list`

List all configured providers.

```bash
theoria auth list
```

### `theoria auth status`

Check authentication status for a provider.

```bash
theoria auth status PROVIDER
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
