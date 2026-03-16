---
name: image-generation
description: 画像生成 — レギュレーション準拠のサムネイル・図解・Mermaid・4コマ漫画・Xグリッド・クイズ画像を生成するスキル
---

# 画像生成スキル
**対象領域: note/X コンテンツ用画像**

`scripts/generate_image.py` を使い、レギュレーションとリファレンス画像に基づいた一貫性のある画像を生成する。

## Use this skill when
- 記事のサムネイル（アイキャッチ）画像が必要なとき
- 記事内の図解・概念図が必要なとき
- フローチャート・構造図・パイプライン図が必要なとき（Mermaid）
- 4コマ漫画（ストーリー型ビジュアル）が必要なとき
- X投稿用の画像が必要なとき
- X投稿用のクイズ画像（エンゲージメント用）が必要なとき
- タスクYAMLの `generate_image` アクションを実行するとき

## Do not use this skill when
- 既存画像の編集・切り抜きを求められたとき（Pillow直接操作）
- スクリーンショットを撮るとき（Playwright MCPを使用）

## 依存ファイル

| ファイル | 役割 |
|---------|------|
| `scripts/generate_image.py` | 生成スクリプト本体 |
| `knowledge/sites/note/image-regulation.md` | レギュレーション（正本） |
| `knowledge/sites/note/thumbnail-guide.md` | note表示仕様・デザイン知見 |
| `knowledge/account-concept.md` | カラーパレット・デザイン原則 |
| `knowledge/characters/*/ref_idol.jpg` | キャラ別リファレンス画像（5キャラ分） |
| `config/mermaid-theme.json` | Mermaidテーマ設定（森テーマ） |
| `.env` | `OPENAI_API_KEY`（プロジェクト専用） |

## 画像タイプ一覧（6カテゴリ13タイプ）

### サムネイル (`thumbnail`)
- 16bit ピクセルアート、チビキャラ比率
- `--style` でスタイル切り替え（デフォルト: office）
- `--chars` でリファレンスキャラ指定（カンマ区切り、スタイルのデフォルトを上書き）
- API生成: 1536×1024（3:2横長）→ 後処理で **1280×670（1.91:1）** にクロップ＆リサイズ
- note推奨アスペクト比に最適化。上下110pxクロップのためセーフゾーンをプロンプトに指示済み
- マルチリファレンス: スタイルに応じて複数キャラのリファレンス画像を自動選択

| スタイル | CLI | 構図 | 推奨記事 |
|---------|-----|------|---------|
| オフィス | `--style office` | AIアイドル+ビジネスマンのオフィスシーン | 汎用 |
| 黒板 | `--style blackboard` | 黒板+チョーク文字+教える構図 | 初心者解説 |
| ゲームスタート | `--style game-start` | レトロゲームのキャラ選択画面風 | トレンド |
| RPGステータス | `--style rpg-status` | ステータスバーでAI特性を表現 | AI比較 |
| レトロOS | `--style retro-os` | Win95風デスクトップUI | ガチ回 |
| 2コマ | `--style comic-preview` | ボケ+ツッコミ2パネル | 掛け合い |
| ステージ | `--style idol-stage` | コンサートステージに全員集合 | 特別回 |
| VSバトル | `--style vs-battle` | 格ゲーVS画面の対決構図 | AI対決 |

#### スタイル別デフォルトリファレンス

| スタイル | デフォルトキャラ | 補足 |
|---------|----------------|------|
| office | aiko | — |
| blackboard | aiko | — |
| game-start | 全5キャラ | キャラ選択画面のため全員 |
| rpg-status | aiko | `--chars` で対象キャラ指定可 |
| retro-os | aiko | — |
| comic-preview | aiko | `--chars` で2キャラ指定可 |
| idol-stage | 全5キャラ | ステージに全員集合 |
| vs-battle | aiko, chatgpt | `--chars` で対決キャラ変更可 |

### 図解 (`diagram`)
- 16bit ピクセルアート
- 説明対象が中央、マスコットキャラが端に小さく配置
- 紫〜ピンクのグラデーション背景
- 日本語ラベルOK（枠付きバナー内）
- 生成・保存: 1024×1024
- オプション: `--layout board` でボード型レイアウト（複雑な図解向け）

### Mermaid図 (`mermaid`)
- mmdc (mermaid-cli) でレンダリング。**OpenAI API不使用・無料**
- テーマ: `config/mermaid-theme.json`（森テーマ：深緑背景＋緑ノード）
- 用途: フローチャート、構造図、パイプライン図、状態遷移図、システム解説
- ソース: インラインコード / `.mmd` ファイル / `.md` 内の ```mermaid ブロック

| サイズ | CLI | 解像度 | 用途 |
|--------|-----|--------|------|
| X投稿 | `--size x` | 1200×675 | X投稿画像（デフォルト） |
| note図解 | `--size note` | 1536×1024 | note記事内の図解 |
| ワイド | `--size wide` | 1920×1080 | フルHD解説・プレゼン |
| 正方形 | `--size square` | 1024×1024 | 汎用 |

#### 投稿用の設計ルール
- **TB（上→下）レイアウト推奨**: LR（左→右）は横に伸びて投稿画像に不向き
- **ノード上限**: X=10-15、note=20、ワイド=25 程度
- **絵文字OK**: ノードラベルに絵文字を使うと視認性が上がる
- **日本語OK**: ノードラベル・エッジラベル共に日本語対応

#### コンテンツ活用例
- **裏側公開**: 自動化パイプラインの仕組みを図で見せる
- **AI解説**: Claude Code / エージェント / LLMのアーキテクチャ図
- **比較図**: ツール選択のフローチャート
- **ノウハウ図解**: ワークフロー手順の視覚化

### 4コマ漫画 (`comic`)
- 16bit ピクセルアート、縦長4パネル
- マスコットキャラが全パネルに一貫登場
- AIロボットが共演、起承転結のストーリー
- 各パネル下部に日本語ラベル（2-4文字）
- 紫〜ピンクのグラデーション背景
- 生成・保存: 1024×1536

### Xグリッド投稿 (`x-grid`)
- 16bit ピクセルアート、横長4枚セット
- 各画像が独立した1シーン（独立4回生成、Method C）
- マスコットキャラ + AIロボットが共演
- 起承転結ストーリー（左上→右上→左下→右下）
- 各画像下部に日本語ラベル（2-4文字）
- 生成: 1536×1024 → リサイズ: 1200×675（X推奨 16:9）
- API呼び出し: 4回（パネルごとに独立生成）

### クイズ画像（X専用、8タイプ）
- 16bit ピクセルアート、正方形カード
- マスコットキャラがプレゼンター役（小さめ）
- CTA（行動喚起バナー）が必須
- 生成・保存: 1024×1024（リサイズ不要）

| タイプ | CLI名 | 用途 |
|--------|-------|------|
| 選択式 | `quiz-choice` | A/B/C/D 4択クイズ |
| ○×クイズ | `quiz-ox` | 正誤判定クイズ |
| 穴埋め式 | `quiz-fill` | 空欄補充クイズ |
| ランキングあて | `quiz-ranking` | 順位予想クイズ |
| 間違い探し | `quiz-spot` | 左右比較で違いを探す |
| 設問式 | `quiz-open` | 自由回答の質問 |
| 数値あて | `quiz-number` | 数値予想クイズ |
| Before/After | `quiz-ba` | 前後比較クイズ |

## 実行方法

```bash
# サムネイル（デフォルト: office スタイル）
python scripts/generate_image.py thumbnail "シーンの説明" --topic トピック名

# サムネイル（スタイル指定）
python scripts/generate_image.py thumbnail "ChatGPTの基本的な使い方" --topic chatgpt-basics --style blackboard
python scripts/generate_image.py thumbnail "AI選択ガイド2026" --topic ai-select --style game-start
python scripts/generate_image.py thumbnail "Claude vs ChatGPT 文章力対決" --topic claude-vs-chatgpt --style vs-battle
python scripts/generate_image.py thumbnail "Claude Codeで自動化できること" --topic claude-code --style retro-os
python scripts/generate_image.py thumbnail "Geminiのステータス分析" --topic gemini-status --style rpg-status
python scripts/generate_image.py thumbnail "AIアイドル月間ベスト" --topic monthly-best --style idol-stage
python scripts/generate_image.py thumbnail "ChatGPTあるある" --topic chatgpt-araru --style comic-preview

# サムネイル（キャラ指定で vs-battle の対決キャラを変更）
python scripts/generate_image.py thumbnail "Gemini vs Grok トレンド力対決" --topic gemini-vs-grok --style vs-battle --chars gemini,grok

# 図解（デフォルト）
python scripts/generate_image.py diagram "図解の内容" --topic トピック名

# 図解（ボード型 — 複雑なフロー・比較表向け）
python scripts/generate_image.py diagram "AIワークフローの比較表" --topic workflow --layout board

# 4コマ漫画
python scripts/generate_image.py comic "テーマの説明" --topic トピック名 --story "1:ラベル|説明 2:ラベル|説明 3:ラベル|説明 4:ラベル|説明"

# Xグリッド投稿（4枚独立生成）
python scripts/generate_image.py x-grid "テーマの説明" --topic トピック名 --story "1:ラベル|説明 2:ラベル|説明 3:ラベル|説明 4:ラベル|説明"

# クイズ — 選択式（--quiz-data で選択肢指定）
python scripts/generate_image.py quiz-choice "AIが得意な作業はどれ？" --topic ai-task --quiz-data "Q:問題文|A:選択肢A|B:選択肢B|C:選択肢C|D:選択肢D"

# クイズ — ○×
python scripts/generate_image.py quiz-ox "AIは人間の仕事を100%代替できる" --topic ai-myth

# クイズ — 穴埋め
python scripts/generate_image.py quiz-fill "AIが自動化できるのは＿＿＿である" --topic ai-auto

# クイズ — ランキング（--quiz-data で項目指定）
python scripts/generate_image.py quiz-ranking "AI活用率が高い業務TOP3" --topic ai-ranking --quiz-data "1:議事録作成|2:データ分析|3:???|?:あなたの予想は？"

# クイズ — 間違い探し
python scripts/generate_image.py quiz-spot "AIロボットの部屋で間違いを探せ" --topic ai-spot

# クイズ — 設問式
python scripts/generate_image.py quiz-open "AIを使って一番効率化したい作業は？" --topic ai-question

# クイズ — 数値あて
python scripts/generate_image.py quiz-number "日本企業のAI導入率は何%？" --topic ai-stat

# クイズ — Before/After
python scripts/generate_image.py quiz-ba "AI導入前と後の議事録作成" --topic ai-ba

# Mermaid図 — インラインコード
python scripts/generate_image.py mermaid "graph TB; A-->B; B-->C" --topic pipeline --size x

# Mermaid図 — .mmd ファイル指定
python scripts/generate_image.py mermaid --mmd diagrams/flow.mmd --topic agent-arch --size note

# Mermaid図 — .md ファイル内の N 番目の mermaid ブロック抽出
python scripts/generate_image.py mermaid --mmd knowledge/pipeline-map.md --mmd-index 0 --topic pipeline --size x
```

### Claude Code から呼ぶ場合
```
Bash: cd "プロジェクトルート" && python scripts/generate_image.py thumbnail "..." --topic ...
```

## プロンプト設計原則

### プロンプト構造（OpenAI推奨順序）
```
[Reference Image]: リファレンス画像の役割ラベル
↓
背景/シーン設定
↓
被写体の詳細
↓
重要なディテール（色・パレット・小物）
↓
制約条件（NG項目）
↓
User request: ユーザーの具体的な依頼
```

### 鉄則
1. **プロンプト分離**: サムネイル・図解・4コマ漫画・Xグリッド・クイズ各種のルールを絶対に混在させない
2. **リファレンスラベル**: 画像の用途を明示する（`style reference` / `character reference`）
3. **英語プロンプト推奨**: 画像生成AIは英語の方が精度が安定する
4. **品質**: `quality="high"` を常に使用
5. **NG制約はプロンプト末尾に**: 禁止事項を最後にまとめて明記する
6. **一発で完璧を目指さない**: 生成→確認→プロンプト調整のサイクルを回す

### サムネイル専用テクニック

#### ピクセルアート暴走防止
AIはディテールを足す方向に暴走しやすい。以下を全て明示して抑える:

| 要素 | 指定すべき内容 |
|------|--------------|
| ビット数 | `8-bit style` |
| パレット | `limited color palette, maximum 16 colors` |
| アングル | `slight isometric overhead view` |
| ドット粒度 | `coarse large pixels, no anti-aliasing` |
| キャラ比率 | `small chibi-style characters (2-3 heads tall)` |

#### カイロソフト風の再現キーワード
`16-bit SNES style` + `isometric` + `chibi characters` + `limited palette` + `warm indoor lighting`

#### ネガティブスペース
サムネイルの上部にタイトル用の余白を確保したい場合は「leave negative space in the upper third for title overlay」を指定

### 図解専用テクニック

#### キャラクター一貫性
外見特徴を**5項目以上**列挙する（曖昧な形容詞は使わない）:

```
pink twin-tails hair, purple idol outfit with gold trim,
gold star brooch on chest, sapphire blue eyes (hex #0F52BA),
pixel blush on cheeks, white boots with purple accents
```

- 「cute」「cool」等のムードワードは禁止（ドリフトの原因）
- 色は具体的に: `blue eyes` → `sapphire blue eyes (hex #0F52BA)`
- 保持文を入れる: `Do not change her face, outfit, hair color, or accessories in any way.`

#### 図解のレイアウト制御
- 概念ブロックは最大4つまで（それ以上は情報過多）
- フロー図は矢印で接続、各ブロックは枠付きバナー内
- キャラは端に小さく（画面の15-20%以内）

#### ボード型レイアウト（`--layout board`）
- 複雑な図解（フロー図・比較表・手順リスト・段階図）のときに使う
- 黒板/ホワイトボードが画面の60-70%を占め、図解はボード面上に描画される
- **キャラ配置**: ボードの完全に外側（左端 or 右端の下部）に配置。ボード上のテキスト・図と絶対に重ならないこと
- キャラサイズは小さめ（画像幅の15-20%）。ボード内容が優先
- ボードの枠がピクセルアートの情報を整理する自然な区切りになる
- 使い分け: シンプルな概念図→デフォルト、複雑なフロー/テーブル→ボード型

### 4コマ漫画専用テクニック

#### ストーリー設計
- 起承転結の4ビート構成。最終パネルにオチ（ユーモア推奨）
- 各パネルのアクションはテキストなしでも理解できる視覚的表現を心がける
- AIロボットとの絡みで「あるある」ネタが刺さりやすい

#### パネル一貫性
- キャラクターが全4パネルで同一デザインであることが最重要
- プロンプトに `Character design must NOT change between panels` を必ず含める
- パネル間の背景色は微妙な変化OK（同系色グラデーション内）

#### ラベル設計
- 各パネルのラベルは **2-4文字** が最適（「残業の山」「AI発見！」「全自動！」「...え？」等）
- オチのパネルは記号や省略形で意外性を出す（「!?」「...」）
- ラベルはバナー内に配置し、パネル下部に統一

### Xグリッド専用テクニック

#### Method C（独立4回生成）を選んだ理由
- 1枚の画像を分割する方式（Method A）は、Xが自動挿入するギャップで継ぎ目が破綻する
- 独立生成なら各画像が自己完結するため、ギャップが自然に見える

#### ストーリー設計（X向け）
- 左上→右上→左下→右下の読み順を意識する
- 各画像が単体でも意味が通じるようにする（タイムラインでは1枚ずつ拡大表示される）
- オチ（右下）はインパクト重視。テキストオチよりビジュアルオチが効果的

#### キャラクター一貫性（独立生成の課題）
- 4回の独立生成のためキャラデザインが微妙にブレる可能性あり
- リファレンス画像 + 外見特徴の詳細列挙で抑制する
- 許容範囲内のブレは「表情変化」として受容する

### クイズ画像専用テクニック

#### 正方形フォーマットを選んだ理由
- 横長(16:9)で生成→リサイズするとクロップで上下が切れる
- 正方形(1:1)はXタイムラインで目立ち、クロップ不要で全要素が表示される
- クイズカードは情報密度が高いため、切れリスクを排除する正方形が最適

#### CTA（行動喚起）の設計
- 画像下部にCTAバナーを必ず配置（「コメントで回答!」「リプライ!」等）
- CTAがあることでユーザーのアクション率が大幅に向上する
- タイプごとにCTA文言を変える（選択式→「コメントで回答!」、○×→「○か×でリプライ!」等）

#### `--quiz-data` の使い分け
- **選択式**: `"Q:問題文|A:選択肢A|B:選択肢B|C:選択肢C|D:選択肢D"` — 問題文と4択を指定
- **ランキング**: `"1:項目|2:項目|3:???|?:あなたの予想は？"` — 番号付き項目、???で隠し枠
- **その他**: `--quiz-data` なしでOK。プロンプト本文にクイズ内容を含める

#### 間違い探しのコツ
- 1枚の画像内に左右分割で描かせる（2枚の独立生成ではなく）
- 違いは3箇所が適切（多すぎると見つからない、少なすぎると簡単すぎる）
- 左右に「左」「右」のラベルを必ず付ける

### 日本語テキストのコツ
- gpt-image-1.5 は日本語対応だが、漢字の正確性は完璧ではない
- **大きい見出し（2-4文字）のみ信頼可能**。長文・小さい文字は精度が落ちる
- 高コントラストの枠付きバナー内に配置を指示する
- テキストは引用符で囲む: `The label reads "初回探索"`
- 化けが許容できない場合は英語ラベルにフォールバック
- **後載せ戦略**: 精密なテキスト配置が必要な場合は画像生成後にCanva等で文字入れ

### 生成後の日本語チェック

画像生成後、Read で画像を確認する際に以下を必ずチェック:
- [ ] 表示テキストがすべて日本語か（英語ラベルが混入していないか）
- [ ] ラベルの日本語が正しく読めるか（文字化けしていないか）
- 英語テキストが見つかった場合 → プロンプトに `ALL text MUST be Japanese` を追加して再生成

## 保存ルール
- 保存先: `knowledge/data/images/`
- 命名:
  - 通常: `note_{type}_{topic}_{YYYY-MM-DD}.jpg`
  - Xグリッド: `x_grid_panel-{1-4}_{topic}_{YYYY-MM-DD}.jpg`
  - クイズ: `x_{quiz-type}_{topic}_{YYYY-MM-DD}.jpg`
  - Mermaid: `mermaid_{topic}_{YYYY-MM-DD}.png`（PNG固定・mmdc出力そのまま）
- 1記事あたり上限: サムネイル1枚 + 図解3枚 + 4コマ漫画2枚 + Xグリッド1セット(4枚) + クイズ2枚まで

## トラブルシューティング

| 問題 | 原因 | 対策 |
|------|------|------|
| オフィスシーンが図解/4コマに混入 | プロンプトにサムネイルルールが混在 | タイプ別ルールのみ注入されているか確認 |
| キャラが複数体出現 | プロンプトで「1体のみ」の指定が弱い | 「Character appears exactly ONCE」を強調 |
| 日本語テキスト化け | gpt-image-1.5 の漢字限界 | 短いラベル、枠付き配置、または英語フォールバック |
| API 403 エラー | 組織認証未完了 | `images.edit()` API を使用（Responses API は認証必要） |
| モデル not found | モデル名の誤り | `gpt-image-1.5` を使用（`gpt-image-1` も利用可） |
| 4コマのパネル数が4以外 | プロンプトの指定が弱い | 「Exactly 4 panels, no more, no less」を強調 |
| 4コマでキャラデザインが変わる | パネル間の一貫性指定不足 | 「Character design must NOT change between panels」を追加 |
| Xグリッドでキャラがブレる | 独立4回生成のため | リファレンス画像 + 外見特徴5項目以上を明示。許容範囲内は受容 |
| X投稿時にギャップで破綻 | 1枚分割方式を使用した | Method C（独立4回生成）を使用する。分割方式は非推奨 |
| クイズ画像の上下が切れる | 横長で生成してクロップした | 正方形(1024x1024)で生成する。リサイズ不要 |
| クイズのCTAが表示されない | プロンプトでCTA指定が弱い | 各クイズタイプ専用プロンプトにCTA文言が組み込み済み |
| 間違い探しの違いが不明瞭 | 1枚内左右分割の精度限界 | シンプルなシーンを指定。複雑な背景は避ける |

## タスクYAMLでの使い方

```yaml
- action: generate_image
  type: thumbnail
  prompt: "AIエージェントがデータ分析をしている風景"
  topic: data-analysis
  skill: image-generation

- action: generate_image
  type: thumbnail
  style: blackboard     # スタイル指定（省略時は office）
  prompt: "プロンプトの基本を解説"
  topic: prompt-basics
  skill: image-generation

- action: generate_image
  type: x-grid
  prompt: "AIに議事録を任せたら"
  topic: meeting-minutes
  story: "1:会議3時間|疲れた表情で居眠り 2:完璧な議事録|AIが差し出す議事録に驚く 3:上司も絶賛|サムズアップ 4:…結論|もう一回会議しましょう"
  skill: image-generation

- action: generate_image
  type: quiz-choice
  prompt: "AIが得意な作業はどれ？"
  topic: ai-task
  quiz_data: "Q:AIが最も得意な作業は？|A:議事録作成|B:コーヒーを淹れる|C:社内政治|D:有給申請"
  skill: image-generation

- action: generate_image
  type: quiz-ox
  prompt: "AIは人間の仕事を100%代替できる"
  topic: ai-myth
  skill: image-generation
```
