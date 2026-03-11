# 参考プロジェクト・技術リファレンス

Browser Worker の設計に参考となるプロジェクトの整理。

---

## 1. ブラウザ自動化エージェント

### 1.1 browser-use
- **リポジトリ**: https://github.com/browser-use/browser-use
- **概要**: Python + Playwright。AIエージェントにブラウザ操作能力を付与

### 1.2 Vercel agent-browser
- **リポジトリ**: https://github.com/vercel-labs/agent-browser
- **概要**: AIエージェント向けヘッドレスブラウザ CLI。Snapshot-Ref パターン

---

## 2. SNS・コンテンツ自動化

### 2.1 postiz-agent
- **リポジトリ**: https://github.com/gitroomhq/postiz-agent
- **概要**: SNS投稿自動化 CLI。28+ プラットフォーム対応

### 2.2 social-media-agent（LangChain）
- **リポジトリ**: https://github.com/langchain-ai/social-media-agent
- **概要**: ソーシング -> キュレーション -> スケジューリングの3段階 + human-in-the-loop

---

## 3. 取り入れ状況

| 参考要素 | 出典 | 状態 |
|---|---|---|
| Snapshot-Ref パターン | agent-browser | 採用済み |
| 認証を人間に委譲 | 独自 | 採用済み |
| ステップ間データ受け渡し | Skyvern, LaVague | 採用済み |
| ナレッジ自動蓄積 | 独自 | 採用済み |
| Committee Review | 独自（social-media-agent に類似思想） | 採用済み |
| 3段階パイプライン（生成->レビュー->投稿） | social-media-agent | 採用済み |
