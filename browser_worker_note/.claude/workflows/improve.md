---
description: 実行ログとレポートから改善点を抽出し、次回運用へ反映するワークフロー
---

# /improve ワークフロー

`/research` と `/run-task` の結果、各種レポート、セッションログをもとに改善案を固め、必要なファイル更新まで行う。

## 使い方

```
/improve [x|note|both] [任意のフォーカス]
```

例:
- `/improve x`
- `/improve both リサーチから投稿までの詰まり`
- `/improve note ダッシュボード分析の改善`

---

## このワークフローの責務

- 直近の実行結果から勝ち筋と失敗要因を抽出する
- 単発ノイズと継続シグナルを分ける
- `knowledge/`, `tasks/`, `.claude/workflows/` のどこを直すべきか決める
- 必要なら小さな修正をその場で適用する
- 次回試す実験を 1-3 件に絞る
- セッションログと改善ログに記録する

**やらないこと**
- 根拠の薄い大規模方針転換
- 1件だけの結果をもとにした投稿戦略の全面変更
- 公開・投稿の実行

---

## 起動時に必ず読むファイル

1. `memory/session-log.md`
2. `config/policies.yaml`
3. `knowledge/x-content-queue.md`
4. `knowledge/sites/x/posting-strategy.md`
5. `knowledge/sites/x/report-design.md`
6. `knowledge/content-types.md`
7. `knowledge/logs/improvements/_template.md`
8. 対象に応じて以下
   - X: `knowledge/logs/x/posts/`, `knowledge/logs/x/weekly/`, `knowledge/logs/x/monthly/`
   - note: `knowledge/logs/note/dashboard/`, `knowledge/sites/note/index.md`, `knowledge/sites/note/article-editor.md`
   - research 起点の改善: `knowledge/logs/research/YYYY-MM-DD.md`, `.claude/workflows/research.md`

---

## 実行手順

### 1. スコープ確定

ユーザー入力から以下を決める。

- 対象: `x / note / both`
- 観点: `research / publish / report / full-loop`
- 基準期間: 指定がなければ直近 14 日

### 2. 証拠集め

読む順番:
1. 直近のセッションログ
2. 直近のレポート類
3. 当該タスク定義
4. 対応する戦略・ナレッジ

#### 2-1. X Search による競合・ベンチマーク分析（X対象時）

対象が `x` または `both` の場合、定量ログだけでなく X Search で定性的な外部シグナルも収集する。

```bash
# 競合アカウントの直近テーマ・傾向を取得
python scripts/x_search.py competitor --period 14d

# ジャンル全体のベンチマーク（自アカウントとの相対位置を把握）
python scripts/x_search.py benchmark --period 30d
```

- 結果は `knowledge/logs/x/research/competitor/` / `benchmark/` に YAML 保存される
- 競合の勝ちパターンは `wins` に、自アカウントとのギャップは `opportunities` に分類する
- `knowledge/logs/x/research/ideas.yaml` に蓄積されたアイデアも確認する

証拠は次の4分類で整理する。

- `wins`: 明確に良かったもの
- `problems`: 再発している失敗・詰まり
- `unknowns`: データ不足で断定できないもの
- `opportunities`: 小さな改善で効きそうなもの

### 3. 変更対象を決める

問題ごとに、どこを直すべきかを1つに寄せる。

- `knowledge/`: UI差分、運用知見、レギュレーション不足
- `tasks/`: 手順抜け、引数不足、分岐不足
- `.claude/workflows/`: 全体の実行順、handoff、改善ループ
- `scripts/`: レポート集計や補助処理の自動化不足

1件の問題に対して変更先を複数に広げすぎない。

### 4. 変更のしきい値

- 同種の失敗が 2 回以上ある: 実ファイルを更新してよい
- 1 回だけだが影響が大きい: 安全側へ寄せる修正のみ可
- まだ観測 1 回で軽微: 改善ログに仮説として残し、次回検証へ回す

### 5. 実施

必要なら、その場で以下を実施する。

- タスクYAMLの軽微修正
- ワークフロー文言の補強
- ナレッジへの追記
- キューの status / notes 更新
- レポートテンプレートや補助スクリプトの修正

### 6. 改善ログ記録

改善を行った場合は `knowledge/logs/improvements/YYYY-MM-DD_<scope>.md` を新規作成または追記し、以下を残す。

- 根拠に使ったレポート / ログ
- 実際に変えたファイル
- 次回確認する指標
- 見送りにした仮説

### 7. セッションログ更新

`memory/session-log.md` に以下を追記する。

- やったこと
- うまくいったこと
- 改善すべきこと
- 発見
- 未完了・引き継ぎ

---

## 出力フォーマット

最終出力は以下の4部構成にする。

### 1. 主要シグナル

- 何が効いているか
- 何が詰まっているか

### 2. 今回適用した改善

- 変更ファイル
- 変えた理由

### 3. 次回の実験

- 最大 3 件
- 成功判定の指標付き

### 4. 次に回すコマンド

例:

```text
/research Claude Code
/run-task x-post-report post_id: ...
/run-task x-report-rollup mode: weekly
```

---

## 運用ルール

- 直近データが空なら、改善ではなく「計測不足」として返す
- 月間レポートがない段階で大きなローテーション変更はしない
- X の戦略変更は `posting-strategy.md` と `x-content-queue.md` を必ず両方確認する
- note の改善は公開記事とダッシュボード差分の両方を見る
- 改善を実施したら、次回どの指標で検証するかまで明記する
