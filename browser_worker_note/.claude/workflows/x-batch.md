---
description: X投稿の3日分ストックを維持する一気通貫ワークフロー。データ取得→レポート→ストック充足を1コマンドで回す
---

# /x-batch ワークフロー

「Xの投稿をお願い」と言われたら、このワークフローで **3日分のストック（12枠）** を充足状態にする。

## 使い方

```
/x-batch [days: 3]
```

例:
- `/x-batch` ← 3日分（デフォルト）
- `/x-batch days: 5` ← 5日分

---

## 3ステップの全体像

```
① データ取得    ── 過去投稿のメトリクスを最新にする
② レポート確認  ── データを保存し、ダッシュボードで分析する
③ ストック充足  ── 3日分（12枠）になるまでポストを作成・予約する
```

---

## コマンド体系

```
/x-batch（日常の標準コマンド）
  ├─ ① データ取得
  ├─ ② レポート確認 → ★ ユーザー確認
  └─ ③ ストック充足 → /x-post を N回実行 → ★ 各投稿ユーザー承認

/x-post         ← テーマ指定の単発投稿
/trend-sokuhou  ← トレンド速報（枠外割り込み可）
/research       ← ネタ収集（/x-batch とは独立して実行）
/improve        ← 改善抽出（週1推奨）
```

---

## 起動時に読むファイル

1. `knowledge/sites/x/posting-strategy.md` — 配置ルール・パターン10型
2. `knowledge/account-concept.md` — ペルソナ・トーン
3. `knowledge/sites/x/index.md` — 実証済みブラウザフロー
4. `.agent/skills/god-writing/SKILL.md` — 5原則
5. `.agent/skills/god-writing/quality-standards.md` — 品質基準・NGワード

---

## ① データ取得

過去の投稿データを最新にする。

### 1. ストック現状確認

```bash
python scripts/x_analytics.py stock --days {N}
```

空き枠数を把握し、③で作成する本数を確定する。

### 2. 予約→投稿の遷移確認

予約日時が過去のものについて、Xの予約一覧を確認する。

```
1. navigate → /compose/post/unsent/scheduled
2. snapshot で予約一覧を確認
3. なくなっている = 投稿済み → DB の status を 'posted' に更新
```

```bash
python scripts/x_analytics.py update --post-id {id} --imp 0 --eng 0
```

### 3. 直近投稿のメトリクス収集

対象: 投稿後3日以内 かつ 最新取得から24h以上経過

```
1. プロフィールページ（/UaW6wnKW8c87193）→ 投稿一覧
2. 対象投稿の /{post_id}/analytics を開く
3. imp / eng / detail / profile / likes / RT / replies / bookmarks を読み取る
```

```bash
python scripts/x_analytics.py update --post-id {id} \
  --imp {N} --eng {N} --detail {N} --profile {N} \
  --likes {N} --retweets {N} --replies {N} --bookmarks {N}
```

**3日ルール**: 投稿から3日超えたら計測しない。

### 4. DB同期

```bash
python scripts/x_analytics.py queue-sync
```

---

## ② レポート確認

データを保存し、ダッシュボードとCLIレポートで分析する。

### 1. ダッシュボード生成

```bash
python scripts/dashboard.py generate --month {YYYY-MM}
```

### 2. 改善シグナルの読み取り

ダッシュボードの**改善分析**・**クロス分析**ページから以下を確認:

| 項目 | 確認内容 | ③への反映 |
|------|---------|-----------|
| ER=0%投稿 | 何件あるか、共通点は何か | 同じC種別×パターンの組み合わせを避ける |
| 偏り警告 | 特定C種別に偏っていないか | 偏りC種別を避け、別のC種別を優先 |
| 未使用C種別 | 試していないC種別 | 1枠で試す |
| クロス分析 | 最強/最弱の組み合わせ | 最強を再現、最弱を回避 |

### 3. パフォーマンスサマリ

```bash
python scripts/x_analytics.py report --days 14
python scripts/x_analytics.py report --by pattern --days 14
python scripts/x_analytics.py report --by pillar --days 14
```

### 4. 勝ちパターン特定

```yaml
analysis:
  best_pattern: "最もavg_impが高いパターン"
  best_slot: "最もavg_impが高い時間枠"
  worst_combo: "クロス分析の最弱（回避対象）"
  pillar_balance:
    やってみた実演: N件 (目標: 40%)
    埋もれた一次情報のフォーク: N件 (目標: 30%)
    制作の裏側公開: N件 (目標: 30%)
```

### 5. 空きスロットの設計

ストック現状と分析を組み合わせて、各空き枠に何を入れるか設計する。

**設計の優先ルール:**

```
1. posting-strategy.md の配置ルール（曜日×時間帯の推奨パターン）
2. 22:00枠は必ずS級パターン（リプ誘発が最強シグナル）
3. ダッシュボードの偏り警告を反映（偏りC種別を避ける）
4. 柱バランス補正（不足柱を優先）
5. 勝ちパターンを週2回以上使う
6. クロス分析の最弱組み合わせを避ける
```

**枠ごとの必須ルール:**

| 枠 | 時間 | 推奨パターン | 画像 |
|----|------|-------------|------|
| あさいち | 07:00 | 朝tips・共感系 | **必須**（diagram推奨） |
| お昼 | 12:00 | 図解・4コマ・BA（A級） | **必須**（diagram/quiz-ba） |
| 帰宅 | 18:00 | note連動・実用tips | **必須**（diagram/ogp） |
| 深夜 | 22:00 | リプ誘発・お題（S級） | **必須**（diagram/quiz-choice） |

### 6. レポート出力 → ユーザー確認

```
■ X Analytics Report (直近14日)
- 投稿数: N本 (N本/日)
- 平均imp: N / 最高imp: N (記事名)
- 勝ちパターン: XXX (avg_imp=N)
- 柱バランス: やってみた N% / フォーク N% / 裏側 N%

■ 改善シグナル
- 偏り: C6が50% → 他のC種別を優先
- ER=0%: 朝tips×C1が2回 → 回避
- 最強: C2×trend-sokuhou → 再現

■ ストック状況
- 充足: N/12 (N%)
- 空き: N スロット → 今回 N本 作成予定

■ 作成計画
1. 3/17 07:00 [朝] aruaru-kakeai — C4 やってみた実演
2. 3/17 12:00 [昼] tsukaiwake-chart — C6 埋もれた一次情報
3. ...
```

★ ユーザー確認後、③に進む。

---

## ③ ストック充足

空き枠を1本ずつ埋め、3日分（12枠）を充足する。**並列作成はしない**（品質が崩れる）。

### 各投稿の作成フロー

slot_plan の各エントリについて、以下を順次実行する。

#### 1. テーマ確定

優先順:
1. `x-content-queue.md` の Inbox に合致するネタ
2. `knowledge/logs/x/research/ideas.yaml` の未使用ネタ（`status: new`）
3. なければ slot_plan の theme_hint + `account-concept.md` のトーンで生成

#### 2. 本文生成

参照: `x-post.md` Step 2

- 140字以内
- 1つの主張
- ハッシュタグ最大1個
- URL入れない
- 驚き屋NG、メタ前置きNG

#### 3. 画像生成

```bash
python scripts/generate_image.py {type} "{プロンプト}" --topic "{テーマ}" [--layout board] [--chars ...]
```

**全投稿に画像を付ける。例外なし。** パターンIDに応じた image_type を `posting-strategy.md` のパターンID一覧から自動適用。

#### 4. 予約投稿（ブラウザ）

`knowledge/sites/x/index.md` の実証済みフローに従う。

```
1. navigate /compose/post
2. click "ポストを予約"
3. select_option 時 → 分 → 日（時間→日付の順）
4. click "確認する"
5. type (slowly: true) → 本文入力
6. click "画像や動画を追加" → file_upload
7. ★ ユーザー最終承認 ★
8. click "予約設定"
9. snapshot で確認
```

#### 5. DB登録

```bash
python scripts/x_analytics.py add \
  --post-id "pending_{date}_{time}" \
  --date {YYYY-MM-DD} --time {HH:MM} \
  --pattern {パターンID} --pillar {柱} \
  --image-type {画像タイプ} --image-path {画像パス} \
  --topic "{テーマ}" --text "{本文}" \
  --content-type {C分類} --source {ソース} \
  --status scheduled
```

#### 6. 次の投稿へ

slot_plan の次のエントリに進む。全エントリ完了まで 1〜5 を繰り返す。

---

## 完了

### キュー同期 + ストック確認

```bash
python scripts/x_analytics.py queue-sync
python scripts/x_analytics.py stock --days {N}
```

### 完了報告

```
■ X Batch 完了
- 作成: N本
- ストック: N/12 (N%) → 3日分充足 ✅
- 次回の /x-batch 推奨: {空き枠ができる日}

■ 作成した投稿
1. 3/17 07:00 [朝] aruaru-kakeai — C4 img=diagram
2. 3/17 12:00 [昼] tsukaiwake-chart — C6 img=diagram
3. 3/17 18:00 [夕] note連動 — C3 img=ogp
4. 3/17 22:00 [夜] sankagata-odai — C4 img=diagram
```

---

## フロー全体図

```
/x-batch
  │
  ├─ ① データ取得
  │   1. stock → 空き枠把握
  │   2. scheduled→posted 遷移確認（ブラウザ）
  │   3. 直近投稿のメトリクス収集（ブラウザ）
  │   4. queue-sync（DB→queue.md）
  │
  ├─ ② レポート確認
  │   1. dashboard generate（改善分析の最新化）
  │   2. 改善シグナル読み取り（偏り・ER=0%・未使用C種別・クロス分析）
  │   3. パフォーマンスサマリ（CLIレポート）
  │   4. 勝ちパターン特定
  │   5. 空きスロット設計（改善反映）
  │   6. レポート出力 → ★ ユーザー確認 ★
  │
  ├─ ③ ストック充足（slot_plan の各エントリを順次実行）
  │   1. テーマ確定（queue → ideas → 生成）
  │   2. 本文生成（140字）
  │   3. 画像生成（全投稿必須）
  │   4. 予約投稿（ブラウザ）→ ★ 各投稿ユーザー承認 ★
  │   5. DB登録（status=scheduled）
  │   6. → 次の投稿へ
  │
  └─ 完了
      queue-sync + stock確認 + 完了報告
```

---

## 運用ルール

- **3日分ストック**: 常に12枠を目標。空き枠がある限り作成する
- **毎日4投稿**: 07:00 / 12:00 / 18:00 / 22:00。22:00は必ずS級
- **画像必須**: 全投稿に画像を付ける。例外なし（スコア2倍を捨てない）
- **1本ずつ**: 投稿作成は並列しない
- **メトリクスは3日以内**: 投稿から3日超えたら計測しない
- **改善反映**: ダッシュボードの改善分析を毎回確認し設計に反映する
- **承認ポイント**: ②-6（計画確認）+ ③-4（各投稿の最終承認）
- **DB がシングルソース**: queue.md は `queue-sync` で自動生成。手動で直接編集しない（Inbox/Dropped除く）

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `x-post.md` | 単発投稿ワークフロー（本文生成・画像・投稿の詳細） |
| `trend-sokuhou.md` | トレンド速報ワークフロー（枠外割り込み） |
| `scripts/x_analytics.py` | DB管理CLI（stock / queue-sync / report） |
| `scripts/dashboard.py` | ダッシュボード生成（改善分析含む） |
| `knowledge/sites/x/posting-strategy.md` | パターン10型・配置ルール |
| `knowledge/sites/x/index.md` | ブラウザ操作ナレッジ |
