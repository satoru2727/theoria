# コントリビュート

## 開発環境セットアップ

```bash
git clone https://github.com/theoria-project/theoria.git
cd theoria
pip install -e ".[dev]"
```

## コード品質

### リント & フォーマット

```bash
ruff check src tests
ruff format src tests
```

### 型チェック

```bash
mypy src
```

### テスト

```bash
pytest
```

## コードスタイル

- **ruff** でリントとフォーマット（行長100、py311ターゲット）
- **mypy --strict** で型チェック
- すべての公開関数に型ヒントが必要
- 絶対に必要な場合を除きdocstringは書かない
- コメントよりも自己文書化コードを優先

## アンチパターン

避けるべきこと：

- 正当な理由なしの `# type: ignore` や `cast(Any, ...)`
- 空の例外ハンドラ（`except: pass`）
- ハードコードされたプロバイダーキー
- 単純で明白な関数へのdocstring

## プロジェクト規約

### 設定優先度

```
環境変数 > ./config.theoria.yaml > ~/.config/theoria/config.yaml
```

### 新しいエージェントの追加

1. `src/theoria/agents/your_agent.py` を作成
2. フェーズ追跡を持つ `YourState(TypedDict)` を定義
3. ノードとルーティングを持つ `StateGraph` を実装
4. `stream_*` メソッドでストリーミングサポートを追加

### CLIコマンドの追加

```python
# cli.py 内
@app.command()
def your_command(
    option: Annotated[str, typer.Option("--option", "-o", help="説明")] = "default",
) -> None:
    """コマンドの説明。"""
    ...
```

## プルリクエスト

1. フォークしてフィーチャーブランチを作成
2. すべてのチェックがパスすることを確認（`ruff`, `mypy`, `pytest`）
3. 明確なコミットメッセージを書く
4. 変更内容の説明付きでPRを提出

## ライセンス

コントリビュートすることで、あなたの貢献がWTFPLライセンスの下でリリースされることに同意します。
