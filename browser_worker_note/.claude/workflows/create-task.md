---
description: 新しいタスクYAMLを対話的に作成するワークフロー（Claude Code版）
---

# /create-task ワークフロー

新しいブラウザ自動化タスクを対話的に作成する。

## 使い方

```
/create-task <タスク名>
```

例: `/create-task note-article-publish`

---

## 実行手順

### 1. テンプレート読み込み

1. `tasks/_template.yaml` を Read で読み込む
2. タスク名を設定

### 2. ヒアリング

ユーザーに以下を質問する:

1. **どのサイトで作業しますか？** -> `site` フィールド
   - `config/sites.yaml` を Read で読み込み、登録済みサイトを提示する
2. **どんな手順で作業しますか？** -> `steps` フィールド
   - ステップごとに「何をするか」を自然言語で記述してもらう
3. **変動する値はありますか？** -> `params` フィールド
   - 例: 記事テーマ、タグなど毎回変わる値

### 3. YAML生成

1. ヒアリング内容をもとにタスクYAMLを生成
2. Write で `tasks/<タスク名>.yaml` に保存
3. 必要なら `config/sites.yaml` に Edit でサイト情報を追加

### 4. 確認

生成したYAMLの内容をユーザーに提示し、修正があれば Edit で対応する。
