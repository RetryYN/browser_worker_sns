---
description: 登録済みタスクの一覧と概要を表示するワークフロー（Claude Code版）
---

# /list-tasks ワークフロー

登録されているタスクの一覧と概要を表示する。

## 使い方

```
/list-tasks
```

---

## 実行手順

1. Glob で `tasks/*.yaml` を取得する（`_template.yaml` は除く）
2. 各YAMLファイルを Read で読み込み、`name` と `description` と `params` を抽出する
3. 以下の形式で一覧表示する:

```
登録タスク一覧

| タスク名 | 説明 | パラメータ |
|---|---|---|
| note-article-publish | noteに記事を公開する | theme, tags |
```

4. 「`/run-task <タスク名>` で実行できます」と案内する
