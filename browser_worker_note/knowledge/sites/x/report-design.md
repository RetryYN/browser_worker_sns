# X レポート設計 & 入れ替えアルゴリズム

投稿パフォーマンスの計測・評価・ローテーション最適化の設計。
投稿戦略は `posting-strategy.md` を参照。

## スクリプト

```bash
# 週間チェック（毎週金曜の投稿完了後）
python scripts/x_report.py weekly

# 月間チェック + 入れ替え判定（月末）
python scripts/x_report.py monthly

# 特定月を指定
python scripts/x_report.py monthly --month 2026-03

# 単発スコア確認
python scripts/x_report.py score knowledge/logs/x/posts/2026-03-10_月.yaml
```

---

## Xアルゴリズムのスコア構造（オープンソース実数値）

出典: [twitter/the-algorithm-ml](https://github.com/twitter/the-algorithm-ml/blob/main/projects/home/recap/README.md)（heavy_ranker）
※ 2026年1月に xai-org/x-algorithm（Grokベース）へ移行済み。手動重みは廃止されたが、旧重みは傾向の参考として有効。

### X内部スコア（露出判定用）

| エンゲージメント | 重み | いいね比 |
|----------------|------|---------|
| author_reply_back（投稿者がリプに返信） | 75.0 | **150倍** |
| reply | 13.5 | 27倍 |
| profile_click | 12.0 | 24倍 |
| good_click（詳細クリック） | 11.0 | 22倍 |
| retweet | 1.0 | 2倍 |
| fav（いいね） | 0.5 | 1倍（基準） |
| negative_feedback | -74.0 | — |
| report | -369.0 | — |

### 重要な区別

**X内部スコア**と**自アカウントのパターン評価スコア**は目的が異なる:
- X内部: 「この投稿をもっと多くの人に見せるべきか」→ リプライ偏重が合理的
- パターン評価: 「どの投稿パターンが自アカウントに効果的か」→ 量+質のバランスが必要

そのため、入れ替えアルゴリズムではX内部の重みをそのまま使わず、独自の composite_score を使用する。

---

## レポート3層構造

```
個別レポート（各投稿の翌起動日に取得）
  ↓ 集約
週間レポート（金曜の投稿完了後に生成）
  ↓ 集約
月間レポート + 入れ替え判定（月1回、月末に実行）
  ↓
翌月のローテーション更新
```

**入れ替え判定は月1回のみ実行。** 週間レポートはデータ蓄積と振り返り用。

---

## 1. 個別レポート（Post Report）

### タイミング
投稿の翌起動日（投稿から48時間以上経過後）に取得。

### 取得指標

| 指標 | 取得方法 | 用途 |
|------|---------|------|
| インプレッション | Xアナリティクス | リーチ量。曜日×時間帯の正規化に使用 |
| エンゲージメント数 | Xアナリティクス | 総反応量 |
| エンゲージメント率 | エンゲージメント/インプレッション | quality_score の入力 |
| いいね数 | Xアナリティクス | volume_score に使用 |
| リプライ数 | Xアナリティクス | volume_score 最重要成分 |
| RT数 | Xアナリティクス | 拡散力 |
| ブックマーク数 | Xアナリティクス | 実用価値。保存=高関心シグナル |
| プロフィールクリック | Xアナリティクス | フォロー導線 |
| リンククリック | Xアナリティクス | note導線（該当時のみ） |

### レポートフォーマット

```yaml
# 個別レポート
post_id: "YYYY-MM-DD_曜日"
date: 2026-03-12
day: 水
time: "12:00"
pattern: "xgrid-4koma"        # 10パターンのどれか
pattern_rank: "A"              # S/A/B/C
difficulty: "初心者"            # 初心者/中級/上級
topic: "AIに議事録を頼んだら"
characters: ["アイコ", "ChatGPT", "Claude", "Gemini"]

metrics:
  impressions: 0
  engagements: 0
  engagement_rate: 0.0         # %
  likes: 0
  replies: 0
  retweets: 0
  bookmarks: 0
  profile_clicks: 0
  link_clicks: 0

# 自動算出（後述のcomposite_score方式）
scores:
  volume_score: 0.0            # replies×10 + bookmarks×8 + retweets×3 + likes×1
  quality_score: 0.0           # engagement_rate（%をそのまま使用）
  composite_score: 0.0         # 正規化後 0.6×volume + 0.4×quality

notes: ""                      # 定性メモ（バズった理由、失敗要因等）
```

### 保存先
`knowledge/logs/x/posts/YYYY-MM-DD_曜日.yaml`

---

## 2. 週間レポート（Weekly Report）

### タイミング
金曜の投稿作成完了後に生成。対象は前週の月・水・金の3投稿。
**判定は行わない。データ蓄積と定性振り返り用。**

### 集計内容

```yaml
# 週間レポート
week: "2026-W11"
period: "2026-03-09 ~ 2026-03-13"

summary:
  total_impressions: 0
  total_engagements: 0
  avg_engagement_rate: 0.0
  total_replies: 0
  total_bookmarks: 0
  avg_composite_score: 0.0

# 今週使った3パターンのスコア
patterns_used:
  - pattern: "dotchi-taiketsu"
    day: 月
    composite_score: 0.0
    engagement_rate: 0.0
  - pattern: "xgrid-4koma"
    day: 水
    composite_score: 0.0
    engagement_rate: 0.0
  - pattern: "dokuzetu-review"
    day: 金
    composite_score: 0.0
    engagement_rate: 0.0

# 曜日×時間帯の効果
timeslot_performance:
  月_20:00: { engagement_rate: 0.0, replies: 0, impressions: 0 }
  水_12:00: { engagement_rate: 0.0, replies: 0, impressions: 0 }
  金_20:00: { engagement_rate: 0.0, replies: 0, impressions: 0 }

best_post: "YYYY-MM-DD_曜日"
worst_post: "YYYY-MM-DD_曜日"

# 定性振り返り
wins: []
improvements: []
discoveries: []
```

### 保存先
`knowledge/logs/x/weekly/YYYY-Www.yaml`

---

## 3. 月間レポート + 入れ替え判定（Monthly Report）

### タイミング
月末（第4金曜 or 最終起動日）に生成。**入れ替え判定もここで実行。**

### 集計内容

```yaml
# 月間レポート
month: "2026-03"
total_posts: 12

summary:
  total_impressions: 0
  total_engagements: 0
  avg_engagement_rate: 0.0
  total_replies: 0
  total_bookmarks: 0
  total_retweets: 0
  avg_composite_score: 0.0
  follower_growth: 0           # 月初→月末

# パターン別の月間成績
pattern_performance:
  - pattern: "dotchi-taiketsu"
    times_used: 1
    avg_composite_score: 0.0
    avg_engagement_rate: 0.0
    trend: "—"                 # ↑ / → / ↓ / —（3ヶ月移動平均の方向）

# 難易度バランス実績
difficulty_balance:
  初心者: { count: 0, ratio: 0.0, target: 0.50 }
  中級:   { count: 0, ratio: 0.0, target: 0.33 }
  上級:   { count: 0, ratio: 0.0, target: 0.17 }

# 曜日×時間帯の月間傾向
timeslot_monthly:
  月_20:00: { avg_engagement_rate: 0.0, avg_replies: 0.0, avg_impressions: 0.0 }
  水_12:00: { avg_engagement_rate: 0.0, avg_replies: 0.0, avg_impressions: 0.0 }
  金_20:00: { avg_engagement_rate: 0.0, avg_replies: 0.0, avg_impressions: 0.0 }

top3: []
worst3: []

# 入れ替え判定結果
rotation_decision:
  promote: []
  demote: []
  hold: []
  replace: []
  experiment: []
  overrides: []                # 難易度バランス補正で上書きされたもの
```

### 保存先
`knowledge/logs/x/monthly/YYYY-MM.yaml`

---

## 入れ替えアルゴリズム（月1実行）

### Step 0: スコア算出（各投稿）

#### volume_score（量の指標）

```
volume_score = replies × 10 + bookmarks × 8 + retweets × 3 + likes × 1
```

| 成分 | 重み | 根拠 |
|------|------|------|
| replies | ×10 | X内部で最重要（13.5pt）。ただし27倍そのままだと他を圧殺するため10に抑制 |
| bookmarks | ×8 | 「後で見返す」意図=高関心。フォロワー継続率に寄与 |
| retweets | ×3 | 拡散力。ただし空RTも多いため控えめ |
| likes | ×1 | ベースライン。X内部でも0.5ptと最低 |

#### quality_score（質の指標）

```
quality_score = engagement_rate（%）
```

インプレッションが少なくてもエンゲージメント率が高い＝刺さっている層がいる。

#### composite_score（総合評価）

```
composite_score = 0.6 × normalize(volume_score) + 0.4 × normalize(quality_score)
```

- normalize: その月の全投稿の中で min-max 正規化（0〜1）
- 量6:質4 の配分。リーチが小さくても率が高いパターンを rescue する設計

### Step 1: 3ヶ月加重移動平均

```
rolling_avg = 当月avg × 0.5 + 前月avg × 0.3 + 前々月avg × 0.2
```

- 月12投稿・各パターン月1-2回では単月判定は統計的に不安定
- 3ヶ月窓で各パターン3-6データポイントに増やす
- 直近月を重く見つつ、ノイズを平滑化

**データ不足時**: 2ヶ月目までは使える月のみで算出。1ヶ月目は当月100%。

### Step 2: ベイズ補正（サンプル数が少ないパターンの補正）

```
adjusted_score = (n × observed_avg + k × global_avg) / (n + k)

n = そのパターンの3ヶ月合計使用回数
k = 3（正則化パラメータ）
global_avg = 全パターンの平均 composite_score
```

- 使用1回 → global_avg に強く引っ張られる（過剰評価/過小評価を防ぐ）
- 使用6回以上 → observed_avg がほぼそのまま反映

### Step 3: パーセンタイルランク

```
全パターンの adjusted_score を降順ソート → 0-100 のパーセンタイルに変換
```

中央値×倍率ではなく相対順位を使う理由:
- 母数5-6パターンでは中央値が1つの外れ値で大きく動く
- 「全パターンが似たスコア」の月でも序列は付く

### Step 4: 判定

```
top 20%      → promote（増枠: 月2→3回）
21-70%       → hold（据え置き）
71-90%       → demote（減枠: 月2→1回）
bottom 10%   → replace候補（差し替え or 内容改善）
使用3回未満  → experiment（実験枠: 翌月に1回は試す）
```

### Step 5: トレンド補正

```
IF 2ヶ月連続で順位下降 → 1段階下方補正（hold→demote等）
IF 2ヶ月連続で順位上昇 → 1段階上方補正（hold→promote等）
```

### Step 6: 外れ値キャップ（バズ対策）

```
IQR = Q3 - Q1（四分位範囲）
上限 = Q3 + 1.5 × IQR
composite_score が上限を超える投稿 → 上限値にクリップ
```

1回のバズで過剰 promote を防ぐ。バズの再現性は低い。

### Step 7: 難易度バランスチェック（最終段、判定を上書き）

```
IF 入れ替え後の初心者向け比率 < 40%:
  → 初心者向けパターンの中で最高スコアのものを promote に上書き
IF 上級向け（ガチ回）が 0:
  → ガチ回スレッドを月1で強制配置
```

**制約は判定より優先。** 上書きされた場合は `overrides` に理由を記録。

### Step 8: 横並び検出

```
IF 全パターンの adjusted_score の標準偏差 < 閾値:
  → 全パターン hold、前月の配置を踏襲
```

差がないのに無理に入れ替えるのは害しかない。

---

## 曜日×時間帯の正規化（補正係数）

月曜夜と水曜昼ではインプレッションの母数が異なるため、同じ volume_score でもパターン間の比較が不公平。

```
timeslot_factor = そのタイムスロットの月間平均インプレッション / 全タイムスロットの月間平均インプレッション
normalized_volume = volume_score / timeslot_factor
```

水曜昼のインプレッションが月曜夜の0.7倍なら、水曜昼の volume_score を 1/0.7 = 1.43倍に補正。

---

## 入れ替え結果の反映

```
1. 月間レポート生成（月末）
2. 入れ替えアルゴリズム実行 → rotation_decision を月間レポートに記録
3. posting-strategy.md の「週3投稿の配置ルール」更新案を作成
4. ユーザーに報告（承認後に確定）
```

### 安全弁まとめ

| 条件 | 動作 |
|------|------|
| データ3ヶ月未満 | replace 判定を出さない（hold 扱い） |
| 月間投稿数 12 未満 | 判定を翌月に持ち越し |
| トレンド速報（パターン10） | 不定期のため入れ替え判定の対象外。記録のみ |
| 横並び（標準偏差 < 閾値） | 全 hold、前月踏襲 |
| 難易度バランス違反 | 制約が判定を上書き |

---

## ディレクトリ構造

```
knowledge/logs/x/
├── posts/                     # 個別レポート
│   ├── 2026-03-10_月.yaml
│   ├── 2026-03-12_水.yaml
│   └── 2026-03-14_金.yaml
├── weekly/                    # 週間レポート
│   ├── 2026-W11.yaml
│   └── 2026-W12.yaml
└── monthly/                   # 月間レポート + 入れ替え判定
    └── 2026-03.yaml
```

---

## 将来の拡張候補

- 時間帯の入れ替え判定（20:00→21:00等）
- キャラ別の人気度トラッキング（どのキャラが出ると composite_score が上がるか）
- note記事との連動効果（X投稿→note流入の相関）
- 季節タグ（年末年始・GW等の異常月を移動平均計算時に重みダウン）
