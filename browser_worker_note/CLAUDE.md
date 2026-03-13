# Delvework Note/X — Claude Code 運用指示

@~/ai-dev-kit-vscode/skills/SKILL_MAP.md
@~/ai-dev-kit-vscode/helix/HELIX_CORE.md

> *Delve into the unknown. Map by touch. Master through repetition.*

## プロジェクト概要

**Delvework（デルヴワーク）** — AIがブラウザを手触りでマッピングし、経験を重ねて精度を上げるブラウザ自動操作の方法論。
探索者（AI）はセッション終了時に消えるが、地図（`knowledge/`）を残して次の探索者に託す。

- 用途: note / X（旧Twitter）への記事・投稿の作成・公開を自動化
- 実行環境: Claude Code + Playwright MCP

## 役割

Claude Code は**設計・実施・改善**の担当者。

1. **設計**: スキル（SKILL.md）、ワークフロー、タスクYAML、ポリシーの新規作成・構造設計
2. **実施**: Playwright MCP を使ったブラウザ操作タスクの実行、ナレッジの蓄積
3. **改善**: 実行結果から得た学びをスキル・ワークフロー・ナレッジにフィードバック

## ワークフローとステップ

詳細は `.claude/workflows/run-task.md` を参照。

### 4つのフェーズ

| # | フェーズ | 条件 |
|---|---------|------|
| 1 | 初回 (First Delve) | サイトナレッジなし |
| 2 | 再訪問 (Return) | ナレッジあり、成功ログなし |
| 3 | 構造変更 (Remap) | 探索中に構造差異検出 |
| 4 | 最適化 (Optimize) | 成功ログ＋短縮メモあり |

### 11のステップ

| Step | Code | 名称 |
|------|------|------|
| A | Order | タスク指令 |
| B | Recon | 外部探索（ファイルベース） |
| C | Probe | 内部探索（ブラウザ） |
| D | Map | マッピング |
| E | Observe | モニタリング（変更前記録） |
| F | Plan | プランニング |
| G | Act | アクション |
| H | Review | レビュー（人間承認） |
| I | Verify | チェック |
| J | Report | レポーティング（差分比較） |
| K | Offer | オファー（成果報告） |

## サイトナレッジの構造

```
knowledge/sites/<site名>/
├── index.md          <- 基本情報・ナビ・探索状況（必須）
├── <page-a>.md       <- ページ単位のフォーム構造
└── ...
```

- `index.md` がハブ。他ファイルへの相互リンクを含む
- ファイル名は英語ケバブケース（例: `article-editor.md`）
- 150行超えたら分割を検討
- 詳細ルールは `.claude/workflows/run-task.md` の D-2 を参照

## 試験運用のサイクル

```
設計 -> 実行 -> 記録 -> 改善 -> 次の実行
```

1. タスク実行前にナレッジ（`knowledge/`）を確認する
2. 実行後は必ずログ（`knowledge/logs/`）とサイト別ノウハウ（`knowledge/sites/`）を記録する
3. 繰り返し発生する問題はスキルやワークフローの改善として反映する

## セッションログ（実験メモリ）

- セッション開始時に `memory/session-log.md` を Read し、前任者の学びを引き継ぐ
- セッション中は自分の行動をメタ認知的に記録する:
  - やったこと（事実）
  - うまくいったこと / 改善すべきこと（振り返り）
  - 発見（次の探索者への知見）
  - 未完了・引き継ぎ事項
- セッション終了前に `memory/session-log.md` を更新する（セクションを追記、古いセッションは残す）

## ソースオブトゥルースと同期ルール

### スキル
- **正**: `.agent/skills/` — Claude Code もここを読む
- `.claude/skills/` は作らない（二重管理を防ぐ）

### ワークフロー
- **正**: `.claude/workflows/`

### 設定・ポリシー・ナレッジ
- `config/`, `knowledge/` は共通（分岐なし）

## committee_review の実装パターン

personas.yaml の Upstream / Downstream / Executor 構造に沿って実行する。

### 推奨構成
- **Upstream / Downstream レビュアー**: Sub-agents（Explore）で並列実行
- **Executor（CEO）**: Opus 本体が統合判断を行う（Sub-agent に委任しない）

### 実行順序
1. **Upstream 先行**: Editor / Marketer が戦略レベルで Go/NoGo 判定
2. **Downstream 後続**: Go なら Editor / Writer が実務レベルで品質チェック
3. **Executor 最後**: Opus 本体が対立点を裁定し最終判断

Upstream で NoGo の場合、Downstream をスキップしてコストを節約する。

### 運用上の注意
- Sub-agent へのプロンプトにはファイルの**絶対パス**を明記する（相対パスは誤解決される）
- 結論は必ず `knowledge/logs/` に記録してからセッションを終える

## HELIX 開発プロセスチェック

タスクを受け取ったら、作業開始前に以下を必ず実行する。

### 1. サイジング（SKILL_MAP.md §タスクサイジング準拠）

| 軸 | S | M | L |
|----|---|---|---|
| ファイル数 | 1-3 | 4-10 | 11+ |
| 変更行数 | ~100 | 101-500 | 501+ |
| API/DB変更 | なし | 片方 | 両方 |

3軸の**最大サイズ**を採用。

### 2. フェーズスキップ（このプロジェクト固有のマッピング）

本プロジェクトのタスクは大きく3種類:

```
├─ ブラウザ操作タスク（/run-task 実行）
│   → Delvework ワークフロー（A-K ステップ）に従う。HELIX フェーズ不要
├─ スキル・ワークフロー・設定の変更（設計系）
│   ├─ S → L4 のみ（直接編集）
│   ├─ M → L2 -> L3 -> L4 -> L6
│   └─ L → フルフロー
└─ ドキュメント・ナレッジの更新
    → L4 のみ
```

### 3. ゲート判定チェックリスト

設計系タスク（M以上）では、以下のゲートを通過すること:

- **G2（設計凍結）**: 変更方針をユーザーに提示し承認を得る
- **G4（実装凍結）**: 変更完了後、影響範囲を確認しユーザーに報告する

### 4. エスカレーション原則

以下に該当する場合は**必ず人間に確認**:
- 公開・投稿を伴う操作（`policies.yaml` の `require_confirmation_before` と連動）
- 認証・決済・個人情報に関わる操作
- 既存ナレッジやスキルの大規模な構造変更

### 5. ファイル作成前チェック

新規ファイルを作成する前に:
1. 既存ファイルで対応できないか確認する
2. 重複するファイルがないか `Glob` / `Grep` で検索する
3. 重複があれば既存ファイルを編集する（新規作成しない）

## ナレッジ参照ガイド

スキルローディング・サブエージェントディスパッチ・C×P別スキル選択表の詳細は以下を参照。

| 正本 | 内容 |
|------|------|
| `.agent/skills/god-writing/SKILL.md` | 5原則 + スキルローディング + C×P別選択表 + T軸OODA重心ガイド |
| `.agent/skills/god-writing/quality-standards.md` | 品質基準（Level 4以上必須）+ レギュレーション |
| `.agent/skills/image-generation/SKILL.md` | 画像生成（CLI・プロンプト設計・保存ルール） |
| `.claude/workflows/generate-content.md` | 記事生成フロー + サブエージェントプロンプトテンプレート |
| `.claude/workflows/research.md` | リサーチフロー |
| `.claude/workflows/x-post.md` | X投稿フロー |

### コンテンツ設計の原則

- 記事 = **内容（C）× 構成パターン（P）× 加工方法（T）**（演出は独立レイヤー）
- **リードに全結論を入れる**（結論を隠して引っ張る構成は使わない）
- **難しい話を噛み砕く方向**が正。既知の常識を声高に投稿しない

## Git

- リモート: `https://github.com/RetryYN/browser_worker_sns.git`
- ブランチ: `main`

## 守るべきルール

- `config/policies.yaml` の禁止事項を厳守する
- ログインは自動実行する（認証情報はブラウザセッションまたは環境変数から取得。ファイルに平文保存しない）
- HELIX 開発プロセスチェックを作業開始前に実行する
