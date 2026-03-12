# Delvework Note/X — 計画

## 1. 目的

note と X（旧Twitter）へのコンテンツ発信を自動化する。
Claude Code + Playwright MCP でブラウザ操作を行い、記事作成・投稿・分析を効率化する。

## 2. 対象サイト

| サイト | 用途 | 主な操作 |
|--------|------|---------|
| note | 長文記事 | 記事作成・編集・公開・ダッシュボード確認 |
| X | 短文投稿 | ポスト・スレッド・記事告知 |

## 3. タスク候補

### note
- 記事ドラフト作成（テーマ -> 構成 -> 執筆）
- 記事公開（下書き -> プレビュー確認 -> 公開）
- ダッシュボード分析（PV・スキ・フォロワー推移の収集）

### X
- 単発ポスト（記事告知、日常発信）
- スレッド投稿（長めのコンテンツをスレッド形式で）
- 個別投稿レポート（views・リプライ・リポスト・いいね等の可視指標収集）

## 4. 実装フェーズ

### Phase 1: サイト探索
- [x] note のダッシュボード・記事エディタをマッピング
- [x] X のホーム・投稿UIをマッピング
- [x] ナレッジファイル作成

### Phase 2: タスク定義
- [x] note-article-publish タスク作成
- [x] note-dashboard-report タスク作成
- [x] x-post-publish タスク作成
- [x] x-idea-post-publish タスク作成
- [x] x-thread-publish タスク作成
- [x] x-post-report タスク作成
- [x] x-report-rollup タスク作成
- [ ] committee_review パイプライン検証

### Phase 3: 運用開始
- [x] research / improve ワークフロー定義
- [ ] 実際の記事で試験運用
- [ ] 実際の投稿でレポート取得と改善ループを検証
- [ ] ナレッジ蓄積・ワークフロー改善

### Phase 4: 統合ダッシュボード
- [x] ダッシュボード設計（`knowledge/sites/common/dashboard-design.md`）
- [x] プラットフォーム設定（`config/platforms.yaml`）
- [x] Post Analysis 拡張（既存 x_report.py 統合）
- [x] Summary セクション実装
- [ ] Competitive Analysis（巡回タスク + 集計 + ベンチマーク）
- [ ] Trend Watch（トレンド収集 + 可視化）
- [x] Algorithm Monitor（異常検知 + ログ）
- [x] System Admin（タスクログ + 可視化）
- [x] 統合ダッシュボード dashboard.py（全セクションHTML統合）
- [ ] マルチテナント対応
