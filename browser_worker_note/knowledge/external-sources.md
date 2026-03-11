# 外部ソース一覧（記事ネタ・技術調査用）

記事テーマの着想、技術的な裏付け、トレンド把握に使う外部ソース。
Recon（外部探索）ステップで参照する。

## AI画像生成系

| ソース | URL | 特徴 | ネタの方向性 |
|--------|-----|------|------------|
| OpenAI Cookbook | cookbook.openai.com | 公式。プロンプトガイド、コード例 | API活用の実践ノウハウ記事 |
| OpenAI Community | community.openai.com | ユーザー投稿。Tips & Tricks スレッド | 現場のハマりポイント・解決法 |
| Zenn (taku_sid) | zenn.dev/taku_sid/articles/image_prompting | ChatGPT画像生成プロンプト完全ガイド | プロンプト設計の体系化記事 |
| Zenn (tomo0108) | zenn.dev/tomo0108/articles/bb3fd613bce479 | ドット絵素材制作ツール比較 | AI×ピクセルアートの制作フロー |
| Zenn (idev) | zenn.dev/idev/articles/article-20250323-060242 | AIレトロキャラ創造術 | キャラ一貫性・スプライト生成 |
| Qiita (7mpy) | qiita.com/7mpy/items/ea0fdbc9893f1fe21cac | GPT-Image-1.5 プロンプト完全ガイド | 最新モデルの使いこなし |
| Qiita (kabumira) | qiita.com/kabumira/items/d9c21630b21c6e6aab30 | GPT-Image 1.5 日本語テキスト注意点 | 日本語テキスト描画の限界と対策 |
| GitHub (awesome-gpt4o-images) | github.com/jamez-bondos/awesome-gpt4o-images | 40個のプロンプト+画像例集 | スタイル別プロンプトカタログ |
| GitHub (openai-cookbook) | github.com/openai/openai-cookbook | 公式チュートリアル群 | API実装パターン |
| GitHub (Pixel-GPT) | github.com/axel578/Pixel-GPT | ピクセルアート生成特化ツール | ツール紹介・レビュー記事 |

## AI×コンテンツ制作系

| ソース | URL | 特徴 | ネタの方向性 |
|--------|-----|------|------------|
| note.com (alpaka_ai) | note.com/alpaka_ai | AI画像生成の文字入れ実験 | 画像生成の限界と工夫 |
| note.com (fluere_alpha) | note.com/fluere_alpha | レトロゲーム風AI画像 | 80年代アドベンチャーゲーム風生成 |
| note.com (hiro_seki) | note.com/hiro_seki | ChatGPTピクセルアート手順解説 | 初心者向けドット絵生成チュートリアル |
| note.com (yudo_tanaka) | note.com/yudo_tanaka | ピクセルアート×アニメミックス | クリエイティブなスタイルミックス |
| ai-nante.com | ai-nante.com | ChatGPTインフォグラフィック制作 | 図解・ビジュアルコンテンツ制作ノウハウ |
| godofprompt.ai | godofprompt.ai/blog | プロンプトエンジニアリング専門 | プロ向けプロンプト設計パターン |

## キャラクター一貫性・デザイン系

| ソース | URL | 特徴 | ネタの方向性 |
|--------|-----|------|------------|
| karasawanouki.co.jp | karasawanouki.co.jp/blog/bu20250502/ | gen_id によるキャラ再現手法 | 実務でのキャラ一貫性テクニック |
| freelance-life.jp | freelance-life.jp/consistent_chara/ | gen_id 使い方ガイド | フリーランス向けAI活用 |
| shikujiriblogger.com | shikujiriblogger.com/chatgpt-ai-image-3layer-template/ | 3層テンプレート方式 | キャラ管理の体系化手法 |
| Medium (shailesh.7890) | medium.com/@shailesh.7890 | DALL-E 3 キャラ一貫性 | 英語圏のベストプラクティス |
| MyAIForce | myaiforce.com/dalle-3-character-consistency/ | 99%キャラ一貫性ワークフロー | 高精度キャラ再現の実践例 |

## 使い方

### Recon ステップでの活用
```yaml
- action: recon
  sources:
    - knowledge/external-sources.md
  purpose: 記事テーマの着想、技術トレンドの把握、競合記事の調査
```

### 記事ネタの引き出し方
1. カテゴリから関連ソースを選ぶ
2. WebSearch / WebFetch でソースの最新記事を確認
3. 自分のアカウントコンセプト（ピクセルアート × AI ビジネス）との接点を見つける
4. 独自の切り口（実践レポート、比較検証、初心者向け解説）で記事化

### ネタ例
- 「gpt-image-1.5 でカイロソフト風サムネイルを量産する方法」
- 「AI画像生成でキャラクターの一貫性を保つ3つのテクニック」
- 「ピクセルアート×AI — レトロゲーム風ビジュアルブランディングの作り方」
- 「日本語テキスト入り図解をAIで作る限界と実用的な回避策」
- 「OpenAI images.edit() API でリファレンス画像を活用するプロンプト設計」
