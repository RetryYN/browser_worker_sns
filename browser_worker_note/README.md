# Delvework Note/X

> *Delve into the unknown. Map by touch. Master through repetition.*

AIがブラウザを操る——と言えば簡単に聞こえる。
だが実際には、サイトごとに異なるUI、非同期読み込み、モーダル、確認ダイアログ……
**人間が「なんとなく」こなしている操作を、AIは一つずつ学習しなければならない。**

Delvework（デルヴワーク）は、その学習プロセスそのものをシステム化した方法論。

## このプロジェクトの目的

**note** と **X（旧Twitter）** への記事・投稿の作成、公開、計測、改善を、Claude Code 用ワークフローとして自動化する。

- 記事のドラフト作成（テーマ設定 -> 構成 -> 執筆）
- 組織的レビュー（Editor / Marketer / Writer の多角視点）
- note への記事公開
- X への投稿（記事告知、単発ポスト、スレッド）
- X / note のレポート取得
- レポート起点の改善ループ

## 仕組み

```
タスクYAML（何をするか）
    + スキル（どう書くか）
    + ナレッジ（サイトの構造記録）
    = 自動実行
```

1. **タスクYAML** (`tasks/`) — 「noteに記事を公開する」「Xに投稿する」等の手順定義
2. **スキル** (`.agent/skills/`) — 文章生成・画像生成のノウハウ（god-writing, image-generation）
3. **ナレッジ** (`knowledge/sites/`) — サイトのUI構造・操作手順の蓄積
4. **ワークフロー** (`.claude/workflows/`) — タスク実行の制御フロー

## ディレクトリ構成

```
.agent/skills/          <- 文章生成・画像生成スキル（god-writing, image-generation）
.claude/workflows/      <- ワークフロー定義（run-task, create-task 等）
config/
  sites.yaml            <- 対象サイト定義（note, X）
  personas.yaml         <- レビュー用ペルソナ（Editor, Marketer, Writer, CEO）
  policies.yaml         <- 禁止事項・安全ルール
knowledge/
  sites/<site名>/       <- サイト別UI構造ナレッジ
  logs/                 <- タスク実行ログ
tasks/                  <- タスクYAML定義
memory/
  session-log.md        <- セッション間の学び引き継ぎ
```

## 実行方法

Claude Code + Playwright MCP で実行する。

```
# タスク実行
/run-task note-article-publish テーマ: AIエージェントの現在地

# ネタ調査
/research Claude Code

# 改善ループ
/improve x

# X 投稿
/run-task x-post-publish post_text: 新しいnote記事を公開しました

# ネタから1コマンドでX投稿
/run-task x-idea-post-publish theme: Claude Codeで議事録整理が速くなった image_type: diagram

# タスク一覧
/list-tasks

# 新規タスク作成
/create-task x-thread-post
```

## 現在の同梱タスク

- `note-article-publish`: 記事ドラフト生成 → committee review → エディタ入力 → 任意のサムネイル添付 → 公開
- `note-dashboard-report`: note ダッシュボードの主要指標を取得 → YAML保存
- `x-idea-post-publish`: ネタ入力 → 本文生成 → 必要なら画像生成 → 即時投稿または予約投稿
- `x-post-publish`: 単発ポスト入力 → 任意の画像添付 → 即時投稿または予約投稿
- `x-thread-publish`: スレッド本文を分割入力 → 任意の画像添付 → 即時投稿または予約投稿
- `x-post-report`: 単一ポストの分析指標を取得 → 個別レポートYAML保存 → score確認
- `x-report-rollup`: 個別レポートから週間 / 月間レポートを生成
- `/research`: ネタ収集 → 分類 → 実演判定 → 検証 → queue / `/run-task` handoff
- `/improve`: 実行ログとレポートを読み、改善案を反映して次回運用へ接続

画像運用の責務分離:
- 生成レイヤー: note用横長、X用正方形/横長を作り分ける
- 投稿レイヤー: 生成済みファイルをそのまま添付する

## Delvework の哲学

- **探索者は消える、地図は残る**: セッションが終わればAIの記憶は消えるが、`knowledge/` に残した地図が次の探索者を導く
- **推測で動くな、事実を確かめろ**: 操作前に必ず snapshot でページ構造を確認する
- **繰り返しが精度を上げる**: 初回は手探り、2回目からはナレッジを活かして効率化
