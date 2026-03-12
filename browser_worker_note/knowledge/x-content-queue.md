# X Content Queue

`/research` で選別した X 向けネタの管理台帳。
新規候補は `inbox`、実際に使えるものは `ready` に置く。

## Status Rules

- `inbox`: 候補だけ入っている。検証・設計が未完了
- `ready`: 投稿案として使える。本文または画像案まで固まっている
- `scheduled`: 予約投稿済み
- `posted`: 投稿済み
- `dropped`: 見送り

## Inbox

| Added | Title | Type | Pattern | Source | Demo | Verification | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-03-12 | ChatGPT for Excelが来た。数式わからなくても日本語で指示するだけ | update | trend-sokuhou | https://openai.com/index/chatgpt-for-excel/ | partial | verified | inbox | note記事と連動。事務職の「Excelつらい」共感軸 |

## Ready

| Ready At | Title | Type | Pattern | Post Angle | Image Plan | Source | Verification Log | Status |
|---|---|---|---|---|---|---|---|---|
| 2026-03-12 | 例: AI選手権クイズ | update | quiz-senshuken | 新機能を4択に変換 | quiz-choice | https://example.com | knowledge/logs/research/2026-03-12.md | ready |

## Scheduled

| Schedule | Title | Pattern | Asset | Source | Status | Notes |
|---|---|---|---|---|---|---|
| 2026-03-15 20:00 | 例: Xグリッド4コマ | xgrid-4koma | knowledge/data/images/x_grid_panel-1_example_2026-03-12.jpg ほか | https://example.com | scheduled | 水曜昼向け |
| 2026-03-13 20:00 | AIがブラウザ操作して投稿してる裏側 | 裏側公開 + 図解 | knowledge/data/images/note_diagram_ai-posting-flow_2026-03-12.jpg | オリジナル | scheduled | 金曜夜ミサキ層ゴールデンタイム |
| 2026-03-16 20:00 | AIで一番「これは助かった」って場面、なに？ | 参加型お題(sankagata-odai) | knowledge/data/images/note_diagram_ai活用お題_2026-03-12.jpg | オリジナル | scheduled | 月曜夜S級リプ誘発。キャラ被り発生→generate_image.py修正済み |

## Posted

| Posted At | Title | Pattern | Post URL | Source | Follow-up |
|---|---|---|---|---|---|
| 2026-03-12 11:55 | AI効率化あるある（理想10分 vs 現実90分） | 共感あるある + 図解 | https://x.com/UaW6wnKW8c87193/status/2031928511871725955 | オリジナル | 翌日エンゲージメント確認 |

## Dropped

| Date | Title | Reason |
|---|---|---|
| 2026-03-12 | 例: 小さなUI文言変更 | 実読価値が薄い |
