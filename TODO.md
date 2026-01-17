# Theoria Roadmap

Production-ready までのロードマップ。

## Phase 1: Core CLI Experience (MVP)

最低限「使える」状態にする。

- [x] **`chat` コマンド実装** - Theoretikos とのインタラクティブ対話
  - Rich を使った TUI (prompt, streaming output)
  - `/exit`, `/clear`, `/save` などの slash commands
  - Ctrl+C でのグレースフルな終了
- [x] **`init` コマンド実装** - プロジェクト初期化
  - `config.theoria.yaml` テンプレート生成
  - 既存 `.bib` ファイルの検出
  - LaTeX プロジェクト構造の検出
- [x] **Storage 層 (SQLite)** - セッション永続化
  - `aiosqlite` でのセッション保存
  - 対話履歴の保存・復元
  - `theoria history` コマンド

## Phase 2: Research Workflow

研究ワークフローの実現。

- [x] **Bibliography 管理** - `.bib` ファイル操作
  - BibTeX パーサー（pybtex）
  - citation key の自動生成
  - 重複検出・マージ
- [x] **`search` コマンド** - Bibliographos との対話
  - 学術検索 API 連携（Semantic Scholar, CrossRef）
  - 検索結果から BibTeX 自動生成
  - 既存 `.bib` への追記
- [x] **`cite` コマンド** - 引用挿入支援
  - fuzzy search で citation key を検索
  - クリップボードに `\cite{key}` をコピー

## Phase 3: LaTeX Integration

LaTeX 編集の本格サポート。

- [x] **LaTeX utilities** - 編集ユーティリティ
  - `\input{}` / `\include{}` の解決
  - document 構造のパース
  - label/ref の整合性チェック
- [x] **`edit` コマンド** - Graphos との対話
  - ファイル指定での LaTeX 編集
  - diff 表示と承認フロー
  - バックアップ自動作成
- [x] **`compile` コマンド** - LaTeX ビルド
  - `latexmk` / `tectonic` ラッパー
  - エラーメッセージのパース・表示
- [x] **`check` コマンド** - LaTeX チェック (bonus)
  - label/ref 整合性チェック

## Phase 4: Advanced Features

差別化機能。

- [x] **`auth login` コマンド** - OAuth ブラウザフロー
  - `oauth.py` を CLI に接続
  - device code flow オプション
- [x] **Agent orchestration** - マルチエージェント連携
  - Theoretikos → Bibliographos への引き継ぎ
  - 「この主張の根拠を探して」→ 自動検索
  - `research` コマンドで統合セッション
- [x] **Export 機能**
  - 対話ログの Markdown エクスポート
  - 引用付き要約の生成

## Phase 5: Polish & Distribution

リリース準備。

- [x] **Error handling** - ユーザーフレンドリーなエラー
  - API key 未設定時の誘導
  - ネットワークエラーのリトライ
  - rate limit 対応
- [ ] **Documentation** - ユーザードキュメント
  - `mkdocs` でのサイト構築
  - Getting Started ガイド
  - Provider 別セットアップ手順
- [x] **Testing** - テストカバレッジ向上
  - CLI integration tests
  - Agent behavior tests (mock LLM)
- [ ] **Packaging** - 配布準備
  - PyPI 公開
  - Homebrew formula (optional)

---

## Current Status

- [x] CLI 基盤 (Typer + Rich)
- [x] Auth store (API key + OAuth 保存)
- [x] OAuth PKCE 実装
- [x] Config loader (Pydantic + YAML)
- [x] LLMClient (LiteLLM wrapper)
- [x] Theoretikos agent (Socratic dialogue)
- [x] Bibliographos agent (literature search)
- [x] Graphos agent (LaTeX editing)

## Priority

1. **Phase 1 を最優先** - `chat` が動けばツールとして使い始められる
2. Phase 2 は research workflow の核心
3. Phase 3-5 は順次

## Notes

- 外部 API (Semantic Scholar 等) は rate limit に注意
- LaTeX コンパイルは OS 依存が大きいので optional 扱い
- OAuth は provider によって対応状況が異なる（ほとんどは API key で十分）
