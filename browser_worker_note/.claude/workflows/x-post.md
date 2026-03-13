---
description: X投稿をテーマ指定またはおまかせで一気通貫実行するワークフロー
---

# /x-post ワークフロー

テーマを受け取り、本文生成→画像生成→X投稿（即時 or 予約）を一気通貫で実行する。

## 使い方

```
/x-post <テーマ or おまかせ> [pattern: <ID>] [schedule: YYYY-MM-DD HH:mm] [image: none|diagram|quiz-*]
```

例:
- `/x-post Claude Codeで議事録が速くなった`
- `/x-post おまかせ schedule: 2026-03-14 20:00`
- `/x-post おまかせ` ← テーマ・時間・画像タイプすべて自動判断
- `/x-post AI4種の使い分け pattern: tsukaiwake-chart image: diagram`

パターン ID は `knowledge/sites/x/posting-strategy.md` の「パターン ID一覧」を参照。

---

## 他コマンドとの関係

```
/research → ネタ候補 → /x-post（推奨）or /run-task x-idea-post-publish
                                ↓
                          投稿 → x-content-queue.md 更新
                                ↓
                /run-task x-post-report → エンゲージメント計測
                                ↓
                          /improve → 改善抽出
```

- **`/x-post`**: 日常の投稿コマンド。実証済みフローで軽量実行
- **`/run-task x-idea-post-publish`**: A-K 11ステップの正式フロー。初回探索やログ差分比較が必要な場合のみ
- **`/run-task x-post-publish`**: テキスト・画像が準備済みの場合の直接投稿

---

## 起動時に読むファイル

1. `knowledge/x-content-queue.md` — キュー状況
2. `knowledge/account-concept.md` — ペルソナ・トーン
3. `knowledge/sites/x/posting-strategy.md` — パターン10型・配置ルール
4. `knowledge/sites/x/index.md` — 実証済みフロー・注意事項
5. `.agent/skills/god-writing/SKILL.md` — 5原則 + スキルローディング
6. `.agent/skills/god-writing/quality-standards.md` — 品質基準 + テーマ選定の原則

---

## 実行フロー

### 1. テーマ決定

**テーマ指定あり** → そのまま使う
**「おまかせ」** → 以下の順で自動決定:

1. `knowledge/logs/x/research/ideas.yaml` に未使用ネタ（`status: new`）があれば候補に含める
2. `knowledge/x-content-queue.md` の Ready セクションにネタがあればそれを使う
3. 候補が不足する場合、X Search でトピック調査を実行する:
   ```bash
   python scripts/x_search.py topic "<柱に合うキーワード>" --period 7d
   ```
4. なければ、Posted セクションの柱バランスを確認し、不足している柱を選ぶ
   - 3つの柱: やってみた実演 / 埋もれた一次情報のフォーク / 制作の裏側公開
3. `posting-strategy.md` の配置ルール（月=S級リプ誘発、水=A級滞在、金=C/B級蓄積）を参照し、曜日に合ったパターンを選ぶ
4. 選んだ柱+パターンに合うテーマを `knowledge/account-concept.md` のトーンで生成する

**pattern 指定あり** → `posting-strategy.md` のパターンID一覧から推奨 `image_type` / `layout` を自動適用

### 2. 本文生成

参照ファイル（Read する）:
- `knowledge/account-concept.md` — ペルソナ・トーン
- `.agent/skills/god-writing/SKILL.md`

生成ルール:
- 140字以内（無料プラン制限）
- 1つの主張に絞る
- ハッシュタグ最大1個
- URLは本文に入れない
- トーン: 「AIめっちゃ使ってる先輩が隣で見せてくれる感じ」
- 驚き屋ムーブNG（「衝撃」「ヤバい」「神ツール」等は使わない）

### 3. 画像生成（スキップ可）

`image: none` 指定時はスキップ。未指定なら `diagram` をデフォルトとする。

```bash
python scripts/generate_image.py <type> "<テーマを視覚化するプロンプト>" --topic "<テーマ>" [--layout board] [--chars ...]
```

### 4. ブラウザ投稿

参照: `knowledge/sites/x/index.md` の「実証済みフロー」セクション。

#### 即時投稿（schedule 未指定）

```
navigate /home → snapshot → type(slowly:true) → click画像ボタン → file_upload → [人間承認] → clickポストする → snapshot確認
```

#### 予約投稿（schedule 指定）

```
navigate /compose/post → clickポストを予約 → select_option(月/日/年/時/分) → click確認する → type(slowly:true) → click画像ボタン → file_upload → [人間承認] → click予約設定 → snapshot確認
```

### 5. 記録

投稿成功後、以下を更新する:

1. **`knowledge/x-content-queue.md`**
   - 即時投稿 → Posted セクションに追加（投稿URL含む）
   - 予約投稿 → Scheduled セクションに追加
2. **個別レポートログ `knowledge/logs/x/posts/YYYY-MM-DD_曜.yaml`**
   - テンプレート: `knowledge/logs/x/posts/_template.yaml` を参照
   - 必須フィールド: post_id, date, day, time, status, pattern, pattern_rank, difficulty, pillar, topic, post_text, characters, image, image_type, image_layout
   - `post_url`: 即時投稿 → 投稿URL を記入。予約投稿 → 空欄（投稿後に `x-post-report` で埋める）
   - `image_issues`: 画像品質問題があれば記載（キャラ被り等）
   - metrics / scores は 0 のまま（`x-post-report` で計測）
3. **`knowledge/sites/x/index.md`** — 新しい発見があれば追記
4. **`memory/session-log.md`** — セッションログに記録

---

## エスカレーション

- 投稿確定の直前に**必ず人間に最終承認**を求める（ポリシー準拠）
- 承認されるまで「ポストする」/「予約設定」ボタンは押さない

## エラー時

- スクリーンショットを撮って状況を報告する
- ログイン切れの場合: 再ログインを試みる（認証情報はユーザーに確認）
