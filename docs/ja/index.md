# Theoria

**人文学研究＆LaTeX執筆支援エージェントCLI**

Theoriaは、AIエージェントを通じて人文学研究者の論証の明確化、引用管理、LaTeXドキュメント編集を支援するコマンドラインツールです。

## 基本理念

- **引用第一**: 出典のない主張は認めない
- **承認駆動**: エージェントが提案し、人間が承認する
- **ローカル第一**: データはあなたのマシンに留まる
- **プロバイダー非依存**: LLMプロバイダーを自由に選択

## 3つのエージェント

| エージェント | 役割 | フェーズ |
|-------------|------|----------|
| **Theoretikos** | ソクラテス式対話パートナー | 明確化 → 反駁 → 総合 |
| **Bibliographos** | 文献検索・引用管理 | 検索 → 抽出 → 検証 |
| **Graphos** | LaTeX編集アシスタント | 分析 → 編集 → 修復 |

## クイック例

```bash
# プロジェクト初期化
theoria init

# ソクラテス式対話を開始
theoria chat

# APIキー管理
theoria auth add openai --key sk-...
```

## 技術スタック

- Python 3.11+
- [LangGraph](https://github.com/langchain-ai/langgraph) - エージェントオーケストレーション
- [LiteLLM](https://github.com/BerriAI/litellm) - プロバイダー抽象化
- [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) - CLI

## ライセンス

このソフトウェアはパブリックドメイン（WTFPL）でリリースされています。
