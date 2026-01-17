# クイックスタート

## 1. 認証の設定

TheoriaはLLMプロバイダーのAPIキーが必要です。いずれかを選択：

=== "OpenAI"
    ```bash
    theoria auth add openai --key sk-your-api-key
    ```

=== "Anthropic"
    ```bash
    theoria auth add anthropic --key sk-ant-your-api-key
    ```

=== "環境変数"
    ```bash
    export OPENAI_API_KEY=sk-your-api-key
    ```

## 2. プロジェクトの初期化

```bash
cd your-research-project
theoria init
```

デフォルト設定の `config.theoria.yaml` が作成されます。

## 3. 対話を開始

```bash
theoria chat
```

ソクラテス式対話パートナー **Theoretikos** とのインタラクティブセッションが始まります。

### セッション例

```
You: Thesis: SNSは政治的言説を根本的に変えた

Theoretikos: 興味深いテーゼです。より詳しく検討してみましょう。

「根本的に変えた」とおっしゃるとき、具体的にどのような変容を
想定されていますか？
1. 情報拡散の速度？
2. 発言の民主化？
3. 議論そのものの性質？

また、時間的範囲を明確にしていただけますか？いつと比較して変わったのでしょうか？
```

## 4. スラッシュコマンド

チャットセッション中：

| コマンド | 説明 |
|----------|------|
| `/help` | 利用可能なコマンドを表示 |
| `/save` | 現在のセッションを保存 |
| `/status` | 対話状態を表示 |
| `/clear` | 会話履歴をリセット |
| `/exit` | チャットを終了 |

## 5. セッションの再開

```bash
# 保存されたセッション一覧
theoria history

# IDで再開
theoria chat --session ses_abc123def456
```

## 次のステップ

- [設定](configuration.md) - セットアップのカスタマイズ
- [Theoretikos](../agents/theoretikos.md) - ソクラテス式対話について
