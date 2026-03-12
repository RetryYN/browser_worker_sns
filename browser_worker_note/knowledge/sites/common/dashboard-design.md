# 統合ダッシュボード設計

マルチテナント × マルチプラットフォーム対応の分析ダッシュボード。
プラットフォーム固有のレポート設計は各サイトの `report-design.md` を参照。

## アーキテクチャ

```
テナント（アカウント/ブランド）
  └─ プラットフォーム（X / note / Instagram / Threads / ...）
       └─ 6セクション（共通構造）
```

### 2軸の拡張モデル

| 軸 | 現在 | 拡張例 |
|----|------|--------|
| テナント | 自アカウント（1つ） | 複数ブランド運用、クライアント別 |
| プラットフォーム | X, note | Instagram, Threads, YouTube, TikTok |

**テナント追加時**: `config/platforms.yaml` にテナントエントリ追加 + `knowledge/logs/<tenant>/` ディレクトリ作成
**プラットフォーム追加時**: `config/platforms.yaml` にプラットフォーム定義追加 + `<platform>_report.py` 作成

---

## UI構造

```
┌─────────────────────────────────────────────────────┐
│  [テナント ▼]    [統合] [X] [note] [Instagram] ...   │  ← メインタブ
├─────────────────────────────────────────────────────┤
│                                                     │
│  （選択中タブの内容）                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### タブとセクションの対応

| タブ | セクション | 役割 |
|------|-----------|------|
| **統合** | Summary / Competitive / Trend Watch / Algorithm / System | 全プラットフォーム横断の分析・管理 |
| **X** | Post Analysis（X固有） | X投稿のパフォーマンス分析 |
| **note** | Post Analysis（note固有） | note記事のパフォーマンス分析 |
| **Instagram** | Post Analysis（Instagram固有） | 将来拡張 |
| **Threads** | Post Analysis（Threads固有） | 将来拡張 |

- 統合タブ: クロスプラットフォームの俯瞰。競合・トレンド・アルゴリズム・システムはここに集約
- プラットフォームタブ: そのプラットフォーム固有の指標・分析軸で Post Analysis を表示
- テナント切替: マルチテナント時のみ表示
- レスポンシブ: 1カラム（モバイル）/ 2カラムグリッド（デスクトップ）
- テーマ: ダークモード（--bg: #0f1117）

---

## 統合タブのセクション

### 1. Summary（概況）

全プラットフォーム横断の KPI 俯瞰 + ベンチマーク対比 + 前期比較。

| 指標 | 説明 | データソース |
|------|------|-------------|
| プラットフォーム別投稿数 | 各PFの投稿件数 | <platform>/posts/*.yaml |
| プラットフォーム別リーチ | インプレッション / PV | 各PF の metrics |
| 全体エンゲージメント率 | 全PF加重平均 | 各PF の engagement 指標 |
| フォロワー増減 | PF別の成長率 | monthly/*.yaml |
| ベンチマーク対比 | 競合中央値との差分 | competitive/benchmark.yaml |
| 前週比 / 前月比 | トレンド方向 | weekly/*.yaml / monthly/*.yaml |
| クロスPF効果 | X投稿→note流入等の相関 | 将来実装 |

#### 表示要素
- スコアカード（PF別）: 主要KPI + 前期比（↑↓→）
- 折れ線グラフ: PF別のリーチ・エンゲージメント推移（重ね表示）
- ベンチマーク対比バー: 自アカウント vs 競合中央値 vs 競合上位25%

---

## プラットフォームタブのセクション

### Post Analysis（投稿分析）— 各PF固有

各プラットフォームタブで表示。指標・分析軸はPFごとに異なる。

#### X タブの Post Analysis

| 分析軸 | 内容 | 可視化 |
|--------|------|--------|
| 投稿一覧 | 全投稿のスコア・指標テーブル | ソート可能テーブル |
| パターン別効果 | 10パターンの composite_score 比較 | 横棒グラフ |
| 柱別バランス | 3本柱の投稿数比率 + 柱別スコア | ドーナツ + バー |
| 難易度別分布 | 初心者/中級/上級 の比率 vs 目標 | ドーナツ |
| 曜日×時間帯 | エンゲージメント率のヒートマップ | ヒートマップ |
| 画像タイプ別 | 画像タイプごとのスコア比較 | 横棒グラフ |
| 画像品質問題 | image_issues のリスト | テーブル |

#### note タブの Post Analysis

| 分析軸 | 内容 | 可視化 |
|--------|------|--------|
| 記事一覧 | 全記事の PV・スキ・コメント テーブル | ソート可能テーブル |
| カテゴリ別 | 記事カテゴリごとの PV 比較 | 横棒グラフ |
| PV推移 | 記事公開後の PV 変化 | 折れ線グラフ |
| スキ率 | PV あたりスキ率の分布 | 散布図 |

#### プラットフォーム固有の指標マッピング

| プラットフォーム | 主要指標 | スコア算出 | 詳細設計 |
|----------------|---------|-----------|---------|
| X | impressions, likes, replies, retweets, bookmarks | composite_score | `sites/x/report-design.md` |
| note | PV, スキ, コメント | TBD | TBD |
| Instagram | reach, likes, comments, saves, shares | TBD | TBD |
| Threads | views, likes, replies, reposts | TBD | TBD |

各PF の Post Analysis の詳細仕様は、そのPF の `report-design.md` に記載。

---

## 統合タブのセクション（続き）

### 2. Competitive Analysis（競合分析）

5アカウント（設定変更可）の追跡 + サマリー + ベンチマーク。

#### データ収集

```
ブラウザ巡回（月次）
  ↓
個別ログ: knowledge/logs/<platform>/competitive/accounts/<account_id>/YYYY-MM.yaml
  ↓ 集約
サマリー: knowledge/logs/<platform>/competitive/summary/YYYY-MM.yaml
  ↓ 基準値算出
ベンチマーク: knowledge/logs/<platform>/competitive/benchmark.yaml
```

#### 個別アカウントログ（月次）

```yaml
# 競合アカウント月次ログ
account_id: "example_account"
account_name: "表示名"
platform: "x"
month: "2026-03"
collected_at: "2026-03-31T20:00:00"

profile:
  followers: 0
  following: 0
  total_posts: 0
  bio_keywords: []           # プロフィールのキーワード

activity:
  posts_count: 0             # 月間投稿数
  avg_posts_per_week: 0.0
  post_types:                # 投稿タイプの内訳
    text_only: 0
    with_image: 0
    with_video: 0
    thread: 0

engagement:
  avg_likes: 0.0
  avg_replies: 0.0
  avg_retweets: 0.0
  avg_bookmarks: 0.0
  avg_engagement_rate: 0.0
  median_impressions: 0      # 取得可能な場合

top_posts:                   # エンゲージメント上位3件
  - url: ""
    text_preview: ""
    likes: 0
    replies: 0
    topic_tags: []            # 手動 or 自動分類

content_themes: []            # その月の主要テーマ
format_trends: []             # 使っているフォーマット（図解、スレッド等）
notable_changes: ""           # 戦略変更の兆候
```

#### サマリー（月次）

```yaml
# 競合サマリー
platform: "x"
month: "2026-03"
generated_at: "2026-03-31T21:00:00"

overview:
  total_accounts_tracked: 5
  avg_posting_frequency: 0.0   # 全アカウント平均（週あたり）
  engagement_leaders: []       # エンゲージメント率上位アカウント

comparative_table:             # 自アカウント vs 競合
  - account: "self"
    followers: 0
    posts_month: 0
    avg_engagement_rate: 0.0
    avg_likes: 0.0
    avg_replies: 0.0
  - account: "competitor_1"
    followers: 0
    posts_month: 0
    avg_engagement_rate: 0.0
    avg_likes: 0.0
    avg_replies: 0.0

theme_trends:                  # ジャンル全体で伸びている話題
  - theme: ""
    accounts_covering: 0
    avg_engagement_boost: 0.0  # テーマ投稿 vs 通常投稿の比

format_trends:                 # 伸びているフォーマット
  - format: ""
    adoption_rate: 0.0         # 使っているアカウントの割合
    avg_engagement_rate: 0.0

insights: []                   # 定性的な気づき
action_items: []               # 自アカウントへの示唆
```

#### ベンチマーク（ローリング更新）

```yaml
# 競合ベンチマーク基準値
platform: "x"
updated_at: "2026-03-31"
window: "3months"              # 算出期間

posting_frequency:
  median: 0.0                  # 週あたり投稿数
  p75: 0.0                     # 上位25%ライン

engagement:
  likes:
    median: 0.0
    p75: 0.0
  replies:
    median: 0.0
    p75: 0.0
  retweets:
    median: 0.0
    p75: 0.0
  bookmarks:
    median: 0.0
    p75: 0.0
  engagement_rate:
    median: 0.0
    p75: 0.0

growth:
  follower_growth_rate:
    median: 0.0                # 月間フォロワー増加率（%）
    p75: 0.0

content:
  image_usage_rate: 0.0        # 画像付き投稿の割合
  thread_rate: 0.0             # スレッド投稿の割合
  avg_post_length: 0           # 平均文字数
```

#### 表示要素
- レーダーチャート: 自アカウント vs 競合平均（5軸: 投稿頻度・いいね・リプライ・RT・成長率）
- 比較テーブル: アカウント横並び
- ベンチマーク対比バー: 自分の位置（中央値・上位25%ライン付き）
- トレンドハイライト: 伸びているテーマ・フォーマット

---

### 3. Trend Watch（トレンド観測）

ジャンル全体の話題・フォーマット動向を追跡。競合分析とは独立して、より広い視野で市場を見る。

#### データ収集

```
ブラウザ巡回（月次）+ external-sources.md のソース
  ↓
トレンドログ: knowledge/logs/<platform>/trends/YYYY-MM.yaml
```

#### トレンドログ（月次）

```yaml
# トレンド観測ログ
platform: "x"
month: "2026-03"
collected_at: "2026-03-31"

hot_topics:                    # 盛り上がっている話題
  - topic: ""
    heat_level: "high"         # high / medium / low
    relevance: "high"          # 自アカウントとの関連度
    example_posts: []          # 参考投稿URL
    actionable: true           # ネタとして使えるか

emerging_formats:              # 新しい投稿フォーマット
  - format: ""
    adoption_stage: "early"    # early / growing / mainstream
    effectiveness: ""          # 効果の所感
    example: ""

platform_changes:              # プラットフォーム仕様変更
  - change: ""
    impact: "medium"           # high / medium / low
    action_needed: ""

audience_shifts:               # ターゲット層の動き
  - observation: ""
    evidence: ""

opportunities: []              # 自アカウントが取り込めるネタ候補
threats: []                    # 注意すべき変化
```

#### 表示要素
- トピックバブルチャート: 話題 × 関連度 × 盛り上がり度
- タイムライン: 月ごとのトレンド変遷
- 機会カード: actionable なネタ候補の一覧

---

### 4. Algorithm Monitor（アルゴリズム変動）

エンゲージメント率の統計的異常を検知し、プラットフォームの仕様変更を記録。

#### 異常検知ロジック

```
週次の avg_engagement_rate を時系列で保持
  ↓
移動平均 ± 2σ の範囲を逸脱 → アラート
  ↓
手動確認 → 原因記録（仕様変更 / バズ / 外部要因）
```

#### 変動ログ

```yaml
# アルゴリズム変動ログ
knowledge/logs/<platform>/algorithm/YYYY-MM.yaml

platform: "x"
month: "2026-03"

anomalies:                     # 自動検知された異常
  - week: "2026-W11"
    metric: "engagement_rate"
    expected: 2.5              # 移動平均
    actual: 5.1
    deviation_sigma: 2.3
    cause: ""                  # 手動記入

spec_changes:                  # プラットフォーム仕様変更
  - date: "2026-03-15"
    description: ""
    source: ""                 # 情報ソースURL
    impact_assessment: ""
    action_taken: ""

baseline:                      # 基準値（ローリング更新）
  engagement_rate_mean: 0.0
  engagement_rate_std: 0.0
  impressions_mean: 0
  impressions_std: 0
  window_weeks: 12             # 算出に使う週数
```

#### 表示要素
- 折れ線グラフ: エンゲージメント率推移 + 2σバンド
- イベントマーカー: 仕様変更のタイムスタンプ
- アラートリスト: 未確認の異常値

---

### 5. System Admin（システム管理）

タスク実行状況、エラー、ナレッジ更新の追跡。

#### データソース

| データ | ソース |
|--------|--------|
| タスク実行ログ | knowledge/logs/system/tasks/YYYY-MM.yaml |
| エラーログ | knowledge/logs/system/errors/YYYY-MM.yaml |
| ナレッジ更新 | git log -- knowledge/ |
| スキル利用 | knowledge/logs/system/skills/YYYY-MM.yaml |

#### タスク実行ログ

```yaml
# システムタスク実行ログ
month: "2026-03"

executions:
  - task: "x-post-publish"
    timestamp: "2026-03-10T20:00:00"
    status: "success"          # success / failure / partial
    duration_sec: 120
    error: ""
    retries: 0

summary:
  total_executions: 0
  success_rate: 0.0
  avg_duration_sec: 0.0
  most_common_errors: []

knowledge_updates:
  - file: ""
    date: "2026-03-10"
    change_type: "update"      # create / update / delete
    description: ""
```

#### 表示要素
- 成功率ゲージ: タスク実行の成功率
- エラーテーブル: 直近のエラーリスト
- タイムライン: ナレッジ更新履歴
- ヒートマップ: タスク実行頻度（日×時間帯）

---

## ディレクトリ構造

```
knowledge/logs/
├── <platform>/                    # x / note / instagram / threads
│   ├── posts/                     # 個別投稿ログ
│   ├── weekly/                    # 週次レポート
│   ├── monthly/                   # 月次レポート
│   ├── competitive/               # 競合分析
│   │   ├── accounts/<id>/         # アカウント別月次ログ
│   │   ├── summary/               # 月次サマリー
│   │   └── benchmark.yaml         # ベンチマーク基準値
│   ├── trends/                    # トレンド観測
│   ├── algorithm/                 # アルゴリズム変動
│   └── dashboard/                 # 生成されたHTML
├── system/                        # システム管理
│   ├── tasks/
│   ├── errors/
│   └── skills/
└── note/                          # note固有（既存）
    └── dashboard/

# マルチテナント時
knowledge/logs/<tenant_id>/
└── <platform>/
    └── （上記と同じ構造）
```

---

## スクリプト構成

```
scripts/
├── dashboard.py               # 統合ダッシュボード生成（メイン）
│   ├── 全セクションのHTMLを1ファイルに統合
│   ├── プラットフォームタブ切替（JS）
│   ├── セクションタブ切替（JS）
│   └── Chart.js 4.x CDN
├── x_report.py                # X固有の集計・スコア算出（既存）
├── note_report.py             # note固有の集計（新規）
├── competitive_report.py      # 競合データ収集・分析（新規）
│   ├── 巡回タスクとの連携
│   ├── サマリー生成
│   └── ベンチマーク算出
└── algorithm_monitor.py       # アルゴリズム変動検知（新規）
    ├── 時系列異常検知
    └── アラート生成
```

### CLI インターフェース

```bash
# 統合ダッシュボード生成
python scripts/dashboard.py generate --month 2026-03 --open
python scripts/dashboard.py generate --month 2026-03 --platform x
python scripts/dashboard.py generate --tenant brand_a --month 2026-03

# 競合分析
python scripts/competitive_report.py collect --platform x    # ブラウザ巡回でデータ収集
python scripts/competitive_report.py summary --month 2026-03 # サマリー生成
python scripts/competitive_report.py benchmark               # ベンチマーク更新

# アルゴリズム変動チェック
python scripts/algorithm_monitor.py check --platform x
python scripts/algorithm_monitor.py log-change --platform x --description "..."
```

---

## 設定ファイル

設定は `config/platforms.yaml` に集約。詳細はそのファイルを参照。

```yaml
# 概要（詳細は config/platforms.yaml）
tenants:
  default:
    platforms: [x, note]
    competitive:
      x: [account_1, account_2, ...]  # 5アカウント
```

---

## 実装フェーズ

| # | 内容 | 依存 |
|---|------|------|
| 1 | config/platforms.yaml 作成 | — |
| 2 | Post Analysis 拡張（既存 x_report.py のダッシュボード統合） | 1 |
| 3 | Summary セクション実装 | 2 |
| 4 | Competitive Analysis（巡回タスク + 集計 + ベンチマーク） | 1 |
| 5 | Trend Watch（トレンド収集 + 可視化） | 4 |
| 6 | Algorithm Monitor（異常検知 + ログ） | 2 |
| 7 | System Admin（タスクログ + 可視化） | 1 |
| 8 | 統合ダッシュボード dashboard.py（全セクション統合HTML） | 2-7 |
| 9 | マルチテナント対応（テナント切替UI + ディレクトリ分離） | 8 |

---

## 将来の拡張候補

- リアルタイムダッシュボード（定期自動更新 + ブラウザ通知）
- レポート自動配信（Slack / メール / note記事化）
- AI要約（月次レポートの自然言語サマリー自動生成）
- クロスプラットフォーム相関分析（X投稿→note流入の因果推定）
- A/Bテスト管理（投稿パターンの意図的な比較実験追跡）
