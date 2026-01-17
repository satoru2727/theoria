# 設定

Theoriaは階層化された設定システムを使用します：

1. **環境変数**（最優先）
2. **プロジェクト設定**（`./config.theoria.yaml`）
3. **グローバル設定**（`~/.config/theoria/config.yaml`）

## 設定ファイル

```yaml
# config.theoria.yaml
agent:
  provider: openai      # LLMプロバイダー
  model: gpt-4o         # モデル名
  temperature: 0.7      # 応答の創造性（0.0-1.0）
  max_tokens: null      # 最大応答長（null = プロバイダーのデフォルト）

bibliography:
  default_style: apa    # 引用スタイル
  bib_file: references.bib

latex:
  compiler: pdflatex    # LaTeXコンパイラ
  output_dir: build     # ビルド出力ディレクトリ

providers:
  openai:
    timeout: 120
  anthropic:
    timeout: 120
```

## 環境変数

| 変数 | 説明 |
|------|------|
| `THEORIA_PROVIDER` | デフォルトプロバイダーを上書き |
| `THEORIA_MODEL` | デフォルトモデルを上書き |
| `THEORIA_TEMPERATURE` | temperatureを上書き |
| `OPENAI_API_KEY` | OpenAI APIキー |
| `ANTHROPIC_API_KEY` | Anthropic APIキー |
| `GOOGLE_API_KEY` | Google AI APIキー |

## 対応プロバイダー

| プロバイダー | モデル例 |
|-------------|----------|
| `openai` | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| `anthropic` | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` |
| `google` | `gemini-pro`, `gemini-1.5-pro` |
| `groq` | `llama3-70b-8192`, `mixtral-8x7b-32768` |
| `mistral` | `mistral-large-latest`, `mistral-medium` |
| `deepseek` | `deepseek-chat`, `deepseek-coder` |
| `ollama` | 任意のローカルモデル |

## 認証情報の保存

APIキーは `~/.config/theoria/auth.json` に `600` パーミッションで保存されます。

```bash
# APIキーを追加
theoria auth add openai --key sk-...

# 設定済みプロバイダー一覧
theoria auth list

# 状態確認
theoria auth status openai

# 削除
theoria auth remove openai
```

!!! note "注意"
    環境変数は常に保存されたキーより優先されます。
