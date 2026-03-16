---
description: note競合分析ワークフロー。scan/update/report/mapをnote固有のフローで実行
---

# /competitor-analysis note ワークフロー

note プラットフォームの競合分析。共通NG判定・分類基準は `competitor-analysis.md` を参照。

---

## scan: 新規アカウント探索・登録

### Step 1: noteプラットフォーム内検索

note には API がないため、以下の手法で探索する:

1. **WebSearch**: `site:note.com "AI活用" "やってみた"` 等のクエリ
2. **ブラウザ巡回**: `https://note.com/search?q=<キーワード>&context=note` で検索
3. **公式マガジン起点**: noteマガジン（`@notemagazine`）の「ChatGPT記事まとめ」等からリンクを辿る
4. **ハッシュタグ巡回**: `#AI活用`, `#ChatGPT`, `#生成AI`, `#業務効率化`

検索クエリ設計:
- **ベンチマーク候補**: 「AI 業務 やってみた 自動化 スクショ」「AI 活用事例 実装」
- **NG候補**: 「note AI 稼ぐ 副業 有料記事 プロンプト集」
- **ニュース候補**: 「AI 導入事例 企業 DX」

### Step 2: 分類

→ `competitor-analysis.md` の「6タイプ分類基準」「NG判定チェックリスト」参照

note 固有の判定ポイント:
- **有料記事の中身**: プロンプトテンプレート集だけ → NG / 深い専門知識 → benchmark
- **外部誘導**: LINE・メルマガ → NG / なし or 自社サービス → OK
- **記事の主語**: 「こうすれば稼げる」→ NG / 「やってみたらこうだった」→ benchmark

### Step 3: DB登録

```bash
# ベンチマーク
python scripts/competitor_analytics.py add-account -p note \
  --handle <note_id> --name "<名前>" --category "<カテゴリ>" \
  --type benchmark --cpt "<C×P×T>" \
  --fork-direction "<フォーク方向>" --note "<メモ>"

# NG
python scripts/competitor_analytics.py add-account -p note \
  --handle <note_id> --name "<名前>" --category "NG:<サブカテゴリ>" \
  --type ng --ng-reason "<NG理由>"

# ニュース/リファレンス
python scripts/competitor_analytics.py add-account -p note \
  --handle <note_id> --name "<名前>" --category "<カテゴリ>" \
  --type news --note "<用途>"
```

### Step 4: 重複チェック

```bash
python scripts/competitor_analytics.py accounts -p note
```

---

## update: メトリクス更新

noteの記事メトリクスは公開ページからは取得困難（PVは非公開）。以下の手法:

1. **自アカウントのダッシュボード**: `/sitesettings/stats` でPV・スキ・コメントを取得
2. **公開ページからの推定**: スキ数・コメント数はクリエイターページから確認可能
3. **競合記事のスキ数**: 記事ページ下部に表示

```bash
python scripts/competitor_analytics.py update --article-id <article_id> \
  --likes <スキ数> --views <PV> --comments <コメント数>
```

---

## report: レポート

```bash
python scripts/competitor_analytics.py report -p note              # 全体サマリ
python scripts/competitor_analytics.py report -p note --by account  # アカウント別
python scripts/competitor_analytics.py report -p note --by content-type  # C×P別
python scripts/competitor_analytics.py report -p note --by treatment     # T軸別
python scripts/competitor_analytics.py report -p note --ranking     # スキ順
python scripts/competitor_analytics.py report -p note --patterns    # 伸びてるパターン
python scripts/competitor_analytics.py report -p note --monthly     # 月別
```

---

## map: note コンテンツ構造対照表の更新

`knowledge/sites/note/competitor-mapping.md` を最新のDB状態で更新する。

1. `competitor_analytics.py accounts -p note --type benchmark` で全ベンチマーク取得
2. 各アカウントの記事構造をC×P×Tにマッピング
3. 出現頻度マップ・勝ちパターン・空白地帯を更新
4. NG層との構造差を再確認

### note特有の分析軸

| 軸 | X にはない視点 |
|----|-------------|
| 文字数帯 | 長文（3000字〜）が有利なプラットフォーム。短文だと埋もれる |
| 有料/無料比率 | ベンチマーク層は無料記事で信頼→有料で深堀り |
| シリーズ構成 | 連載形式がnoteの強み。単発よりシリーズがフォロワー獲得に効く |
| サムネイル | 黒板スタイル等のテキスト付きサムネが CTR に直結 |

---

## NG vs Benchmark 構造差（note固有）

| 軸 | Benchmark | NG |
|----|-----------|-----|
| メインテーマ | AI活用・業務効率化 | note×AIで稼ぐ |
| 記事の主語 | 「やってみたらこうだった」 | 「こうすれば稼げる」 |
| スクショ | 自分の業務画面・実行結果 | なし or 汎用的なUI画面 |
| 有料記事 | 深い専門知識の対価 | プロンプトテンプレート集 |
| 外部誘導 | なし or 自社サービス | LINE・メルマガ・Brain |
| 読後行動 | 「自分もやってみよう」 | 「この有料記事を買おう」 |
| 失敗談 | あり（透明性） | なし（成功だけ見せる） |

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `competitor-analysis.md` | 共通NG判定・分類基準 |
| `knowledge/sites/note/competitor-mapping.md` | note 競合分類テーブル |
| `knowledge/sites/note/index.md` | note サイトナレッジ |
| `knowledge/sites/note/article-editor.md` | note エディタ操作 |
