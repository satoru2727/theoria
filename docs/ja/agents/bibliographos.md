# Bibliographos（ビブリオグラフォス）

**文献検索エージェント**

Bibliographosは、学術文献の検索、引用メタデータの抽出、BibTeXエントリの生成を支援します。

## 責務

- 関連する学術文献の検索
- 引用メタデータの抽出
- 適切にフォーマットされたBibTeXエントリの生成
- 引用の完全性の検証
- 引用の追跡可能性の維持

## 検索フェーズ

```mermaid
graph LR
    A[検索] --> B[抽出]
    B --> C[検証]
```

### 1. 検索（Search）

クエリに基づいて関連する学術文献を検索：

- 主要な論文や書籍を特定
- 著者、年、掲載先を記録
- 研究との関連性を評価

### 2. 抽出（Extract）

構造化された引用メタデータを抽出：

- 引用キーの生成（例：`smith2023`）
- エントリタイプの決定（article, book, inproceedings）
- すべての書誌フィールドを取得

### 3. 検証（Validate）

完全性を確認しBibTeXをフォーマット：

- 必須フィールドが存在することを確認
- 著者名を正しくフォーマット
- 特殊文字をエスケープ
- キーの一意性を確保

## BibTeX出力

```bibtex
@article{smith2023,
  author = {Smith, John and Doe, Jane},
  title = {A Study of Something Important},
  year = {2023},
  journal = {Journal of Important Studies},
  volume = {42},
  pages = {1--20},
  doi = {10.1234/example.2023.001}
}
```

## 技術詳細

Bibliographosは引用追跡機能を持つ `StateGraph` を使用：

```python
class Citation(TypedDict):
    key: str
    type: str
    title: str
    authors: list[str]
    year: str
    source: str
    doi: str | None
    url: str | None
    abstract: str | None

class SearchState(TypedDict, total=False):
    messages: list[Message]
    query: str
    phase: Literal["search", "extract", "validate", "end"]
    search_results: list[dict[str, Any]]
    citations: list[Citation]
    bib_entries: list[str]
```

!!! warning "ステータス: 開発中"
    `search` コマンドはまだCLIで利用できません。
    Bibliographosはエージェントとして機能しますが、CLI統合が未完了です。
