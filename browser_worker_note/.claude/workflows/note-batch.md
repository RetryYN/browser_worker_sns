---
description: note記事の4日分ストックを維持する一気通貫ワークフロー。データ取得→レポート→ストック充足を1コマンドで回す
---

# /note-batch ワークフロー

「noteの投稿をお願い」と言われたら、このワークフローで **4日分のストック（校正済み下書き4件）** を充足状態にする。

## 使い方

```
/note-batch [days: 4]
```

例:
- `/note-batch` ← 4日分（デフォルト）
- `/note-batch days: 7` ← 7日分

---

## 3ステップの全体像

```
① データ取得    ── 直近記事のメトリクスを最新にする
② レポート確認  ── データを保存し、分析してストック計画を立てる
③ ストック充足  ── 1記事公開 + 4日分の校正済み下書きを維持する
```

---

## コマンド体系

```
/note-batch（日常の標準コマンド）
  ├─ ① データ取得
  ├─ ② レポート確認 → ★ ユーザー確認
  └─ ③ ストック充足
       ├─ A. 今日の1記事公開 → ★ ユーザー承認
       └─ B. 下書き作成（/research → ネタ帳 → /generate-content × N回）

/generate-content  ← 記事作成の実行エンジン（Phase 1-2 + note固有 2.5-3.5）
/research          ← ネタ収集（/note-batch とは独立して実行も可）
```

---

## 起動時に読むファイル

1. `knowledge/note-content-queue.md` — noteネタ帳
2. `knowledge/account-concept.md` — ペルソナ・トーン
3. `knowledge/content-types.md` — C×P×T選択基準
4. `knowledge/sites/note/index.md` — noteサイトナレッジ
5. `.agent/skills/god-writing/SKILL.md` — 5原則
6. `.agent/skills/god-writing/quality-standards.md` — 品質基準・NGワード

---

## ① データ取得

### 1. ストック現状確認

```bash
python scripts/note_analytics.py stock
```

下書きフォルダ（`knowledge/drafts/note_*.md`）をスキャンし、ステータス別の件数を表示。

| ステータス | 意味 | ストック計上 |
|-----------|------|------------|
| 校正済み | 公開可能 | ✅ ストック |
| 検証済み | 校正待ち | ⚠️ あと1ステップ |
| 下書き | 検証・校正待ち | ⚠️ あと2ステップ |
| 投稿済み | 公開完了 | ストック外 |

**ストック = 校正済みの件数。目標は{days}件。**

### 2. 直近記事のメトリクス収集

対象: 公開後1週間以内 かつ 最終取得から24h以上経過

```
1. navigate → https://note.com/akatu_unison
2. 各記事ページで views / likes / comments を読み取る
3. note ダッシュボード（https://note.com/sitesettings/stats）で全体指標も取得
```

```bash
python scripts/note_analytics.py update --article-id {id} \
  --views {N} --likes {N} --comments {N}
```

**1週間ルール**: 公開から1週間超えたら計測しない。

### 3. 下書きステータス同期

投稿済みの下書きのステータスが「校正済み」のままになっていないか確認。
DB に登録済み（article_url あり）の記事に対応する下書きファイルがあれば、ステータスを「投稿済み」に更新する。

---

## ② レポート確認

### 1. ダッシュボード生成

```bash
python scripts/dashboard.py generate --month {YYYY-MM}
```

### 2. パフォーマンスサマリ

```bash
python scripts/note_analytics.py report --days 14
python scripts/note_analytics.py report --by content --days 14
python scripts/note_analytics.py report --by treatment --days 14
python scripts/note_analytics.py report --by day --days 14
```

### 3. 勝ちパターン特定

```yaml
analysis:
  best_content_type: "最もavg_viewsが高いC×P"
  best_day: "最もavg_viewsが高い曜日"
  worst_combo: "PV最低の組み合わせ（回避対象）"
  content_balance:
    ツール紹介(C1): N件
    ノウハウ(C2): N件
    ニュース(C3): N件
    体験(C4): N件
  treatment_balance:
    翻訳(T2): N件
    対比(T7): N件
```

### 4. ネタ帳確認

`knowledge/note-content-queue.md` の Inbox / Ready を確認。
`knowledge/logs/research/` の直近リサーチログも確認し、note向きのネタを拾う。

### 5. 作成計画

ストック現状とパフォーマンス分析を組み合わせて、作成する記事を設計する。

**設計の優先ルール:**

```
1. note-content-queue.md の Ready（リサーチ済み）を最優先
2. content-types.md の C×P×T バランス補正（偏りを避ける）
3. 勝ちパターン再現（高PVだったC×Pを再利用）
4. 直近リサーチログから note 向きネタを拾う
5. 上記で足りなければ /research で新規ネタ収集
```

### 6. レポート出力 → ユーザー確認

```
■ note Analytics Report (直近14日)
- 記事数: N本 (N本/日)
- 平均PV: N / 最高PV: N (記事名)
- 勝ちパターン: C×P (avg_pv=N)
- C×Pバランス: C1 N% / C2 N% / C3 N% / C4 N%

■ ストック状況
- 校正済み（公開可能）: N/4
- 検証済み: N件
- 下書き: N件
- 空き: N記事 → 今回 N本 作成予定

■ 作成計画
1. [公開] note_xxx.md — C×P×T (校正済み → 今日公開)
2. [新規] テーマA — C×P×T (ネタ帳 Ready)
3. [新規] テーマB — C×P×T (/research で新規収集)
```

★ ユーザー確認後、③に進む。

---

## ③ ストック充足

### A. 今日の1記事公開

校正済み下書きがあり、今日まだ未公開であれば1記事を公開する。

**1日1本ルール**: 1日に複数記事を公開しない。

フロー:
1. 校正済み下書きを選択（note-content-queue.md の Ready 順、なければ最も古い校正済みから）
2. `generate-content-note.md` Phase 4（公開フロー）を実行
3. DB登録 + ステータス更新

```bash
python scripts/note_analytics.py add --article-id {id} --date {YYYY-MM-DD} \
  --title "タイトル" --content-type C分類 --treatment T軸 \
  --chars 文字数 --images 画像枚数 --thumb-style blackboard \
  --hashtags "tag1,tag2" --url "https://note.com/akatu_unison/n/{id}" \
  --draft "knowledge/drafts/note_{slug}.md"
```

### B. 下書き作成（ストック充足）

校正済みストックが目標件数未満の場合、不足分の下書きを作成する。
**並列作成はしない**（品質が崩れる）。

#### 各記事の作成フロー

##### 1. ネタ確定（Web検索 → ネタ帳）

優先順:
1. `note-content-queue.md` の Ready にネタがあればそれを使う（リサーチ済み）
2. `note-content-queue.md` の Inbox から有望なネタを検証してReady化
3. `knowledge/logs/research/` の直近ログに note 向きネタがあれば
4. なければ **`/research` を実行**:
   - Web検索（指定URLまたは `external-sources.md` のソース巡回）
   - ネタを分類・判定（`research.md` の手順に従う）
   - **`note-content-queue.md` の Inbox に追記**
   - note 向きと判定 → Ready に昇格

**ネタ帳経由の原則**: Web検索の結果は必ず `note-content-queue.md` に記録してから作成に入る。直接作成フローに飛ばない。

##### 2. 記事生成

`/generate-content` を実行（Phase 1→2）:
- Phase 1: 戦略設計（エンティティ → 価値定義 → C×P×T → アウトライン → ★ユーザー承認）
- Phase 2: 執筆（サブエージェント）→ `knowledge/drafts/note_{slug}.md` 【ステータス: 下書き】

##### 3. 検証・校正

`generate-content-note.md` Phase 2.5→3→3.5 を実行:
- Phase 2.5: ファクトチェック・画像生成・具体性検証 → 【ステータス: 検証済み】
- Phase 3: 校正（Level 4以上必須）
- Phase 3.5: note固有チェック（文字数3,000-8,000字・H2見出し3-6個・画像3-8枚・ハッシュタグ3-5個）→ 【ステータス: 校正済み】

##### 4. ネタ帳更新

作成した記事のネタを `note-content-queue.md` で Ready → Used に更新。

##### 5. 次の記事へ

ストックが目標件数になるまで 1→4 を繰り返す。

---

## 完了

### ストック確認

```bash
python scripts/note_analytics.py stock
```

### 完了報告

```
■ note Batch 完了
- 公開: N本
- 新規下書き作成: N本
- ストック（校正済み）: N/4 → 4日分充足 ✅
- 次回の /note-batch 推奨: {公開でストックが減る日}

■ 作成した下書き
1. note_xxx.md — C×P×T (ステータス: 校正済み)
2. note_yyy.md — C×P×T (ステータス: 校正済み)
```

---

## フロー全体図

```
/note-batch
  │
  ├─ ① データ取得
  │   1. stock → 下書きストック確認
  │   2. 直近記事のメトリクス収集（ブラウザ）
  │   3. 下書きステータス同期
  │
  ├─ ② レポート確認
  │   1. dashboard generate
  │   2. パフォーマンスサマリ（CLIレポート）
  │   3. 勝ちパターン特定
  │   4. ネタ帳確認（note-content-queue.md + research logs）
  │   5. 作成計画
  │   6. レポート出力 → ★ ユーザー確認 ★
  │
  ├─ ③ ストック充足
  │   A. 今日の1記事公開（校正済み下書き → 公開）→ ★ ユーザー承認 ★
  │   B. 下書き作成（4日分ストックになるまで順次実行）
  │      1. ネタ確定（Web検索 → ネタ帳 → Ready化）
  │      2. 記事生成（/generate-content Phase 1-2）
  │      3. 検証・校正（Phase 2.5-3.5）→ 校正済み
  │      4. ネタ帳更新（Ready → Used）
  │      5. → 次の記事へ
  │
  └─ 完了
      stock確認 + 完了報告
```

---

## 運用ルール

- **4日分ストック**: 常に校正済み4件を目標。校正済みがある限り毎日1本公開する
- **1日1記事公開**: 1日に複数記事を公開しない
- **1本ずつ作成**: 記事作成は並列しない（品質が崩れる）
- **メトリクスは1週間以内**: 公開から1週間超えたら計測しない
- **下書きファースト**: ブラウザ投稿は最後の転記作業にすぎない
- **ネタ帳経由**: Web検索の結果は必ず note-content-queue.md に記録してから作成に入る
- **承認ポイント**: ②-6（計画確認）+ ③-A（公開の最終承認）+ ③-B-2（各記事のアウトライン承認）
- **DB がシングルソース**: 公開記事のメトリクスは note_analytics.py で一元管理

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `generate-content.md` | 記事生成共通フロー（Phase 1-2） |
| `generate-content-note.md` | note固有: 検証・画像・校正・公開 |
| `research.md` | リサーチフロー（Web検索 → ネタ帳） |
| `scripts/note_analytics.py` | DB管理CLI（stock / report） |
| `scripts/dashboard.py` | ダッシュボード生成 |
| `knowledge/note-content-queue.md` | noteネタ帳（Inbox / Ready / Used） |
| `knowledge/sites/note/index.md` | noteサイトナレッジ |
| `knowledge/sites/note/article-editor.md` | エディタ操作 |
