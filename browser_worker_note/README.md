# Delvework Note/X

> *Delve into the unknown. Map by touch. Master through repetition.*

AIがブラウザを操る——と言えば簡単に聞こえる。
だが実際には、サイトごとに異なるUI、非同期読み込み、モーダル、確認ダイアログ……
**人間が「なんとなく」こなしている操作を、AIは一つずつ学習しなければならない。**

Delvework（デルヴワーク）は、その学習プロセスそのものをシステム化した方法論。

## このプロジェクトの目的

**note** と **X（旧Twitter）** への記事・投稿の作成と公開を自動化する。

- 記事のドラフト作成（テーマ設定 -> 構成 -> 執筆）
- 組織的レビュー（Editor / Marketer / Writer の多角視点）
- note への記事公開
- X への投稿（記事告知、単発ポスト）

## 仕組み

```
タスクYAML（何をするか）
    + スキル（どう書くか）
    + ナレッジ（サイトの構造記録）
    = 自動実行
```

1. **タスクYAML** (`tasks/`) — 「noteに記事を公開する」「Xに投稿する」等の手順定義
2. **スキル** (`.agent/skills/`) — 文章生成のノウハウ（copywriting, storytelling 等）
3. **ナレッジ** (`knowledge/sites/`) — サイトのUI構造・操作手順の蓄積
4. **ワークフロー** (`.claude/workflows/`) — タスク実行の制御フロー

## ディレクトリ構成

```
.agent/skills/          <- 文章生成スキル（copywriting, storytelling 等）
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

# タスク一覧
/list-tasks

# 新規タスク作成
/create-task x-thread-post
```

## Delvework の哲学

- **探索者は消える、地図は残る**: セッションが終わればAIの記憶は消えるが、`knowledge/` に残した地図が次の探索者を導く
- **推測で動くな、事実を確かめろ**: 操作前に必ず snapshot でページ構造を確認する
- **繰り返しが精度を上げる**: 初回は手探り、2回目からはナレッジを活かして効率化
