---
description: 設定ファイルを編集するワークフロー（Claude Code版）
---

# /edit-config ワークフロー

設定ファイルを編集する。

## 使い方

```
/edit-config [変更内容の説明]
```

例: `/edit-config 新しいサイトを追加して`

---

## 実行手順

### 1. 現状確認

1. 編集対象のファイルを Read で読み込んで現在の内容を確認
2. ユーザーに現在の設定を提示

### 2. 編集実行

1. ユーザーの指示に従って Edit で設定ファイルを編集
2. 変更内容をユーザーに提示して確認を取る
3. 確認OKなら保存

### 編集可能なファイル

- `config/sites.yaml` - サイト定義
- `config/policies.yaml` - 禁止事項・安全ルール
- `config/personas.yaml` - レビュー用ペルソナ
- `tasks/*.yaml` - タスク定義
- `knowledge/_schema.yaml` - ナレッジフォーマット
