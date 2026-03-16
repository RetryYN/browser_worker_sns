---
description: X投稿をテーマ指定またはおまかせで一気通貫実行するワークフロー
---

# /x-post ワークフロー

テーマを受け取り、本文生成→画像生成→X投稿（即時 or 予約）を一気通貫で実行する。

## 使い方

```
/x-post <テーマ or おまかせ> [pattern: <ID>] [schedule: YYYY-MM-DD HH:mm] [image: none|diagram|quiz-*|mermaid]
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
/x-batch（日常の標準コマンド）
  ├─ Phase 1: データ収集 → DB更新
  ├─ Phase 2: 分析 → レポート
  └─ Phase 3: /x-post × N本 → 3日分ストック充足
                    ↓
              /improve → 改善抽出
```

### どれを使う？

```
3日分のストックを充足 → /x-batch（推奨。収集→分析→作成を一気通貫）
テーマが決まっている1本 → /x-post（テーマ→投稿を一気通貫）
テキスト＋画像が準備済み → /run-task x-post-publish（直接投稿）
```

- **`/x-batch`**: 日常運用の標準コマンド。データ収集→分析→ストック3日分補充を一気に回す
- **`/x-post`**: 単発投稿。テーマが決まっていて1本だけ作りたい時
- **`/run-task x-post-publish`**: テキスト・画像が準備済みの直接投稿

---

## 起動時に読むファイル

1. `knowledge/x-content-queue.md` — キュー状況
2. `knowledge/account-concept.md` — ペルソナ・トーン
3. `knowledge/sites/x/posting-strategy.md` — パターン10型・配置ルール・NGワード・note連動
4. `knowledge/sites/x/index.md` — 実証済みフロー・注意事項
5. `.agent/skills/god-writing/SKILL.md` — 5原則 + スキルローディング
6. `.agent/skills/god-writing/quality-standards.md` — 品質基準 + テーマ選定の原則
7. `knowledge/sites/x/competitor-mapping.md` — 競合 C×P×T 対照表

---

## 実行フロー

### 1. テーマ決定

**テーマ指定あり** → そのまま使う
**「おまかせ」** → 以下の優先順で自動決定（上から順に試し、最初にヒットしたものを使う）:

1. **Readyキュー**（最優先） — `knowledge/x-content-queue.md` の Ready セクションにネタがあればそれを使う。/research で検証済みのため品質が高い
2. **ideas.yaml** — `knowledge/logs/x/research/ideas.yaml` に未使用ネタ（`status: new`）があれば候補に含める
3. **柱バランス補正** — 上記で候補がない場合、Posted セクションの柱バランスを確認し、不足している柱を選ぶ
   - 3つの柱: やってみた実演 / 埋もれた一次情報のフォーク / 制作の裏側公開
4. **配置ルール適用** — `posting-strategy.md` の配置ルール（月=S級リプ誘発、水=A級滞在、金=C/B級蓄積）を参照し、曜日に合ったパターンを選ぶ
5. 選んだ柱+パターンに合うテーマを `knowledge/account-concept.md` のトーンで生成する

**pattern 指定あり** → `posting-strategy.md` のパターンID一覧から推奨 `image_type` / `layout` を自動適用

### 1.5. 競合検索（差別化チェック）

テーマ決定後、同テーマ・同切り口の競合投稿を検索し、差別化ポイントを確認する。

#### 検索手順

1. **DB検索**: 競合ベンチマークの既存投稿から類似テーマを探す
   ```bash
   python scripts/competitor_analytics.py report -p x --by topic
   ```

2. **C×P×T対照表チェック**: `knowledge/sites/x/competitor-mapping.md` でテーマのC×P×T近傍を確認
   - 同じ C×P の競合投稿があるか
   - その投稿のフォーク方向は何か
   - 空白地帯（競合が少ないC×P×T）を使えないか

3. **X検索**（任意 — テーマが直近トレンドの場合）:
   ```bash
   python scripts/x_search.py search "<テーマのキーワード>" --period 7d
   ```

#### 差別化判定

| 状況 | アクション |
|------|----------|
| 同テーマの競合投稿なし | そのまま進む |
| 同テーマだが切り口（T軸）が違う | そのまま進む（差別化OK） |
| 同テーマ・同切り口の投稿あり | **T軸を変える** or **具体性で勝つ**（実画面スクショ等） |
| NG層と同じ構造になりそう | **即座にアプローチ変更**。NG vs Benchmark 構造差を再確認 |

#### 出力（本文生成への引き継ぎ）

```yaml
competitor_check:
  similar_posts: 0-N件  # 類似投稿の数
  differentiation: "具体性（実画面スクショあり）で差別化"
  avoid: "C2×P5×T1（試してないリスト型）"  # NG構造
  空白地帯: "C4×P9×T7（体験×ケーススタディ×対比）"  # 可能なら狙う
```

この情報を本文生成時の参照コンテキストに含める。

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
- メタ前置きNG（「正直に言うと」「ぶっちゃけ」「本音」）
- note連動時は「詳細はプロフのnoteへ」で誘導（URLを貼らない）

### 投稿タイミング判断

- `posting-strategy.md` の基本スケジュール（毎日4枠: 07:00/12:00/18:00/22:00）を基準
- schedule未指定 → 次の空き枠に自動配置
- トレンド速報 → 即時投稿可（半減期52分を逃さない。枠外OK）
- note連動 → 18:00枠を優先。note公開と同日〜翌日以内に投稿

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
navigate /compose/post → clickポストを予約 → select_option(時→分→月→日→年) → click確認する → type(slowly:true) → click画像ボタン → file_upload → [人間承認] → click予約設定 → snapshot確認
```

**note連動投稿**（「詳細はプロフのnoteへ」パターン）:
メインポストに「詳細はプロフのnoteへ」と記載し、プロフィールのnoteリンクに誘導する。URLを本文やスレッドに入れないためアルゴリズムの不利を回避できる。

~~**旧: スレッド付き予約投稿**（「詳細はコメント欄に」パターン）~~ — 非推奨。予約投稿の編集モーダルではスレッド追加不可のため運用が煩雑。

### 5. 最終検証

投稿/予約設定の完了後、ブラウザ上で以下を検証する（「張り付けて終わり」にしない）:

1. **予約一覧で確認** — `/compose/post/unsent/scheduled` に遷移し、対象ポストが表示されることを確認
2. **ポストをクリックして詳細確認**:
   - 本文: テキストが正しいか（文字化け・切れがないか）
   - ハッシュタグ: 正しく表示されているか
   - 画像: 添付されているか（プレビュー表示）
   - 予約日時: 指定通りか
   - 誘導文: 「詳細はプロフのnoteへ」が正しく記載されているか（note連動の場合）
3. **検証結果をユーザーに報告** — ✓/✗ で各項目の状態を明示

### 6. 記録

**DB がシングルソース。** 投稿成功後、以下の順で更新する。

#### 6-1. DB登録（必須・最初に実行）

```bash
python scripts/x_analytics.py add \
  --post-id {post_id or "pending_YYYY-MM-DD_HH:MM"} \
  --date YYYY-MM-DD --time HH:MM \
  --pattern パターンID --pillar 柱 \
  --image-type 画像タイプ --image-path 画像パス \
  --topic "テーマ" --text "本文" \
  --content-type C分類 --source ソース \
  --status {posted or scheduled}
```

- 即時投稿: `--post-id {実ID}` `--url {投稿URL}` `--status posted`
- 予約投稿: `--post-id "pending_{date}_{time}"` `--status scheduled`（`/x-batch` Phase 1 で実IDに更新）

#### 6-2. キュー同期

```bash
python scripts/x_analytics.py queue-sync
```

DB の状態から `x-content-queue.md` を自動再生成する。手動で queue.md を編集しない。

#### 6-3. その他（該当時のみ）

- `knowledge/sites/x/index.md` — 新しいブラウザ操作の発見があれば追記
- `memory/session-log.md` — セッションログに記録

---

## エスカレーション

- 投稿確定の直前に**必ず人間に最終承認**を求める（ポリシー準拠）
- 承認されるまで「ポストする」/「予約設定」ボタンは押さない

## エラー時

- スクリーンショットを撮って状況を報告する
- ログイン切れの場合: 再ログインを試みる（認証情報はユーザーに確認）
