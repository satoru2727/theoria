# CLIリファレンス

## グローバルオプション

```bash
theoria --help
```

## コマンド

### `theoria version`

現在のバージョンを表示。

```bash
theoria version
# theoria 0.1.0
```

### `theoria init`

現在のディレクトリで新しいTheoriaプロジェクトを初期化。

```bash
theoria init [--force]
```

| オプション | 説明 |
|------------|------|
| `--force, -f` | 既存の設定ファイルを上書き |

`config.theoria.yaml` を作成し、既存の `.bib` と `.tex` ファイルを検出します。

### `theoria chat`

Theoretikosとのインタラクティブ対話セッションを開始。

```bash
theoria chat [--session SESSION_ID]
```

| オプション | 説明 |
|------------|------|
| `--session, -s` | 保存されたセッションをIDで再開 |

#### スラッシュコマンド

| コマンド | 説明 |
|----------|------|
| `/help`, `/?` | 利用可能なコマンドを表示 |
| `/exit`, `/quit`, `/q` | チャットを終了 |
| `/clear`, `/reset` | 会話履歴をクリア |
| `/save` | セッションをディスクに保存 |
| `/status` | 現在の対話状態を表示 |

### `theoria history`

保存されたチャットセッションを一覧表示。

```bash
theoria history [--limit N]
```

| オプション | 説明 |
|------------|------|
| `--limit, -n` | 表示する最大セッション数（デフォルト: 20） |

## Auth サブコマンド

### `theoria auth add`

プロバイダーのAPIキーを追加。

```bash
theoria auth add PROVIDER --key KEY
```

キーを指定しない場合、安全にプロンプトされます。

### `theoria auth remove`

プロバイダーの認証を削除。

```bash
theoria auth remove PROVIDER
```

### `theoria auth list`

設定されたすべてのプロバイダーを一覧表示。

```bash
theoria auth list
```

### `theoria auth status`

プロバイダーの認証状態を確認。

```bash
theoria auth status PROVIDER
```

## 終了コード

| コード | 意味 |
|--------|------|
| 0 | 成功 |
| 1 | 一般エラー |
| 2 | 無効な引数 |
