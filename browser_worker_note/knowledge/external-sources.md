# 外部ソース一覧

記事ネタの収集・技術調査・トレンド把握に使う外部ソース。
リサーチフロー（`.claude/workflows/research.md`）から参照する。

---

## ソースカテゴリ

| カテゴリ | 略称 | 役割 |
|---------|------|------|
| AIプロバイダ公式 | provider | 新機能・変更点の一次情報 |
| ITトレンド系メディア | trend | 業界動向・市場分析 |
| 技術ブログ | tech-blog | 実践知・ノウハウ |

---

## AIプロバイダ公式（provider）

一次情報の正本。アップデート速報（update）の主ソース。

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| Anthropic Blog | anthropic.com/news | Atom | yes | update |
| Anthropic Docs | docs.anthropic.com | なし | no | howto |
| OpenAI Blog | openai.com/blog | RSS | yes | update |
| OpenAI Cookbook | cookbook.openai.com | GitHub API | yes | howto |
| OpenAI Community | community.openai.com | なし | no | real, howto |
| Google AI Blog | blog.google/technology/ai | RSS | yes | update, trend |
| Google Developers Blog | developers.googleblog.com | Atom | yes | update |
| xAI Blog | x.ai/blog | なし | no | update |
| GitHub Releases (Claude Code) | github.com/anthropics/claude-code | GitHub API | yes | update |
| GitHub Releases (OpenAI) | github.com/openai | GitHub API | yes | update |

---

## ITトレンド系メディア（trend）

業界動向をわかりやすく報道。トレンド解説（trend）の主ソース。

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| ITmedia AI+ | itmedia.co.jp/aiplus | RSS | yes | trend, update |
| 日経クロステック | xtech.nikkei.com | RSS | yes | trend |
| CNET Japan | japan.cnet.com | RSS | yes | trend, update |
| TechCrunch Japan | jp.techcrunch.com | RSS | yes | update, trend |
| The Verge (AI) | theverge.com/ai | RSS | yes | update, trend |
| Impress Watch | watch.impress.co.jp | RSS | yes | trend, howto |

---

## 技術ブログ（tech-blog）

実践知の宝庫。ノウハウ翻訳（howto）の主ソース。表に出にくい良質情報。

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| Zenn (AI タグ) | zenn.dev/topics/ai | RSS | yes | howto, compare |
| Zenn (ChatGPT タグ) | zenn.dev/topics/chatgpt | RSS | yes | howto, real |
| Zenn (Claude タグ) | zenn.dev/topics/claude | RSS | yes | howto, real |
| Qiita (AI タグ) | qiita.com/tags/ai | RSS | yes | howto, compare |
| note (AI タグ) | note.com/hashtag/AI | なし | no | real, howto |
| はてなブログ (AI) | b.hatena.ne.jp/hotentry/it | RSS | yes | howto, trend |

### 注目個人ブログ

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| Zenn (taku_sid) | zenn.dev/taku_sid | RSS | yes | howto |
| Zenn (tomo0108) | zenn.dev/tomo0108 | RSS | yes | howto |
| Zenn (idev) | zenn.dev/idev | RSS | yes | howto |

---

## AI画像生成特化

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| GitHub (awesome-gpt4o-images) | github.com/jamez-bondos/awesome-gpt4o-images | GitHub API | no | howto |
| GitHub (Pixel-GPT) | github.com/axel578/Pixel-GPT | GitHub API | no | howto |
| godofprompt.ai | godofprompt.ai/blog | なし | no | howto |
| ai-nante.com | ai-nante.com | なし | no | howto |

---

## キャラクター一貫性・デザイン系

| ソース | URL | RSS/API | auto_fetch | 主なネタタイプ |
|--------|-----|---------|------------|---------------|
| karasawanouki.co.jp | karasawanouki.co.jp/blog | なし | no | howto |
| freelance-life.jp | freelance-life.jp | なし | no | howto |
| shikujiriblogger.com | shikujiriblogger.com | なし | no | howto |

---

## ネタタイプ対応表

ソースカテゴリとネタタイプの相性。

| | update | compare | howto | trend | real |
|---|--------|---------|-------|-------|------|
| **provider** | **主** | 副 | 副 | - | - |
| **trend** | 副 | - | - | **主** | - |
| **tech-blog** | - | 副 | **主** | - | **主** |

---

## 巡回ルール

### WebFetch 巡回（/research 実行時）
- `auto_fetch: yes`（= WebFetch で取得可能）のソースを `/research` のクイック巡回・定期リサーチで確認
- 取得結果は `knowledge/logs/research/YYYY-MM-DD.md` に蓄積
- RSS/API 列は WebFetch のアクセス先として参考にする

### ブラウザ巡回（/research 実行時）
- `auto_fetch: no`（= WebFetch 不可）のソースは Playwright で巡回
- 前回ログとの差分で新着を判定

### ソース追加ルール
- 新しいソースを見つけたら、このファイルに追記する
- RSS/API の有無を確認して auto_fetch を設定
- 主なネタタイプを記載

### tech-blog 採用基準

tech-blog ソースからネタを拾う際の判定基準。技術ブログは品質が高いがエンジニア向けのため、そのまま転用するとLevel 3（不合格）になる。

| 判定 | 基準 |
|------|------|
| 採用 | ミサキ層の業務に直結する内容（Excel、メール、資料作成等）をAIで解決している |
| 採用 | 難しい概念を噛み砕ける余地がある（翻訳価値が高い） |
| 採用 | 実演可能で、スクショに意味がある |
| 見送り | エンジニア以外に適用しにくい内容（CI/CD、コンテナ、型システム等） |
| 見送り | 噛み砕いても「だから何？」になる内容（ミサキ層の課題と接点がない） |
| 見送り | 既にミサキ層の常識になっている内容（「ChatGPTが便利」レベル） |
