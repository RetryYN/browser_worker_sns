# リサーチログ YYYY-MM-DD

## Scope

- target:
- focus:
- requested_count:

## Sources Checked

| Source | Category | Fetch Mode | New Items | Notes |
|---|---|---|---|---|
|  |  | auto/manual |  |  |

## Candidate Pool

### [候補タイトル]
- Source:
- Source Category:
- Published:
- Neta Type:
- Topic Main:
- Topic Sub:
- Demo Decision: OK / partial / NG
- Demo Memo:
- Verification Status: pending / verified / partial
- Content Type:
- X Pattern:
- Misaki Fit: high / medium / low
- One-line Core:
- Decision: keep / hold / drop

## Selected For Note

### [候補タイトル]
- Why:
- Handoff:
```yaml
theme: ""
source_url: ""
content_type: ""
topic_main: ""
topic_sub: ""
research_brief: ""
verification_log: ""
tags: ""
```

## Selected For X

### [候補タイトル]
- Why:
- Handoff:
```yaml
theme: ""
pattern: ""          # posting-strategy.md のパターンID（例: quiz-senshuken）
image_type: ""       # diagram / quiz-choice / x-grid / thumbnail / none
image_prompt: ""     # 画像生成の補足指示（空ならテーマから自動生成）
layout: ""           # board / （空ならデフォルト）
chars: ""            # aiko,claude 等（空ならデフォルト）
source_url: ""
fact_notes: ""
schedule_at: ""      # 予約投稿日時 YYYY-MM-DD HH:mm（空なら即時）
verification_log: ""
```

## Screenshots

- `knowledge/data/images/research/...`

## Verification Notes

- Confirmed:
- Unconfirmed:
- Hold Expressions:

## Next Actions

```text
# note 記事
/run-task note-article-publish theme: ... source_url: ... content_type: ... topic_main: ... topic_sub: ... research_brief: ... verification_log: ...

# X 投稿（軽量版 — 推奨）
/x-post <テーマ> [pattern: <ID>] [schedule: YYYY-MM-DD HH:mm] [image: <type>]

# X 投稿（正式フロー）
/run-task x-idea-post-publish theme: ... pattern: ... image_type: ... source_url: ... fact_notes: ... schedule_at: ...
```
