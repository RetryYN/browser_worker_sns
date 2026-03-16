---
description: X（旧Twitter）競合分析ワークフロー。scan/news/update/report/mapをX固有のフローで実行
---

# /competitor-analysis x ワークフロー

X プラットフォームの競合分析。共通NG判定・分類基準は `competitor-analysis.md` を参照。

---

## scan: 新規アカウント探索・登録

### Step 1: x_search.py でリサーチ

```bash
python scripts/x_search.py search "<検索クエリ>" --period 30d
```

検索クエリ設計:
- **ベンチマーク候補**: 「AI 業務効率化 実際にやってみた スクショ 実演」
- **NG候補**: 「AI 副業 月収 無料配布 プレゼント企画 情報商材」
- **ニュース候補**: 「AI release announcement update model launch」

### Step 2: 分類 → 共通6タイプ基準で判定

→ `competitor-analysis.md` の「6タイプ分類基準」「NG判定チェックリスト」参照

### Step 3: DB登録

```bash
python scripts/competitor_analytics.py add-account -p x \
  --handle <handle> --name "<名前>" --category "<カテゴリ>" \
  --type benchmark --followers <数> \
  --fork-direction "<フォーク方向>" --note "<メモ>"
```

### Step 4: 重複チェック

```bash
python scripts/competitor_analytics.py accounts -p x
```

---

## news: 朝トレンド巡回

### 巡回順序（3層構造）

1. **Layer 1: AIプロバイダー公式**（最優先）
   - @OpenAI, @AnthropicAI, @GoogleAI, @GoogleDeepMind, @MetaAI, @xaboratory

2. **Layer 2: 海外キュレーター**（翻訳フォーク元）
   - @dr_cintas, @rohanpaul_ai, @theAIPostman, @milesdeutscher, @0xSammy

3. **Layer 3: 日本語メディア**（裏取り・補足）
   - @JapanInfoq, @ctgptlb, @noumalization, @AiAircle34052, @denfaminicogame

### 巡回手順

```bash
# 1. トレンド検索
python scripts/x_search.py trend "AI" --period 1d

# 2. 特定プロバイダーの最新情報
python scripts/x_search.py search "from:OpenAI OR from:AnthropicAI release update" --period 3d

# 3. 海外キュレーターの翻訳フォーク元
python scripts/x_search.py search "from:theAIPostman OR from:dr_cintas daily AI" --period 1d
```

### 投稿変換ルール

| ソース | 変換 | C×P×T |
|--------|------|-------|
| 公式リリースノート | 速報+ミサキ層向け一言解釈 | C3×P4×T2 |
| 海外キュレーターのラウンドアップ | 翻訳+「これ、ミサキ層にとってはこういうこと」 | C3×P4×T3 |
| 日本語メディアの速報 | 解釈を加えて差別化（事実だけはNG層と同じ） | C3×P4×T3 |

---

## update: メトリクス更新

```bash
# 投稿メトリクス更新
python scripts/competitor_analytics.py update --post-id <post_id> \
  --likes <数> --retweets <数> --replies <数> --bookmarks <数> --views <数>
```

Playwright で個別投稿の `/status/{post_id}/analytics` ダイアログからメトリクスを取得。

---

## report: レポート

```bash
python scripts/competitor_analytics.py report -p x              # 全体サマリ
python scripts/competitor_analytics.py report -p x --by account  # アカウント別
python scripts/competitor_analytics.py report -p x --by format   # フォーマット別
python scripts/competitor_analytics.py report -p x --by topic    # トピック別
python scripts/competitor_analytics.py report -p x --ranking     # エンゲージ順
python scripts/competitor_analytics.py report -p x --patterns    # 伸びてるパターン
python scripts/competitor_analytics.py report -p x --monthly     # 月別
```

---

## map: X コンテンツ構造対照表の更新

`knowledge/sites/x/competitor-mapping.md` を最新のDB状態で更新する。

1. `competitor_analytics.py accounts -p x --type benchmark` で全ベンチマーク取得
2. 各アカウントの投稿構造をC×P×Tにマッピング
3. 出現頻度マップ・勝ちパターン・空白地帯を更新
4. NG層との構造差を再確認

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `competitor-analysis.md` | 共通NG判定・分類基準 |
| `scripts/x_search.py` | xAI API検索CLI |
| `knowledge/sites/x/competitor-mapping.md` | X 競合 C×P×T 対照表 |
| `memory/project_morning-trend-workflow.md` | 朝トレンドワークフロー方針 |
| `knowledge/sites/x/posting-strategy.md` | X 投稿戦略 |
