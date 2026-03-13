---
description: リサーチ結果から記事・投稿を生成するワークフロー。戦略設計はメイン、執筆・校正はサブエージェントに委任
---

# /generate-content ワークフロー

リサーチハンドオフ（または直接テーマ指示）を受け取り、戦略設計 → 執筆 → 校正のパイプラインで記事・投稿を生成する。

## 使い方

```
/generate-content <テーマ or ハンドオフ> [媒体: note|x] [C×P指定]
```

例:
- `/generate-content "ChatGPT for Excel" 媒体: note C3×P4`
- `/generate-content handoff: knowledge/logs/research/2026-03-12.md#candidate-1`

---

## 責務分担

| レイヤー | 担当 | やること |
|---------|------|---------|
| **メイン（戦略）** | Opus 本体 | エンティティ → 価値定義 → ブランド変容 → スキル選択 → アウトライン構造 → レギュレーション確認 |
| **見出しAgent** | サブエージェント | タイトル10案出し + H2見出しの最終調整 |
| **執筆Agent** | サブエージェント | アウトラインに従って本文生成 |
| **校正Agent** | サブエージェント | 品質判定 + 修正指示 |
| **人間** | ユーザー | アウトライン承認 + 最終レビュー |

**やらないこと**: ブラウザ操作（公開は `/run-task` に渡す）

---

## Phase 1: 戦略設計（メインコンテキスト）

### 1-1. 入力確認

リサーチハンドオフがあれば読む。なければ以下を確定する。

- テーマ（何について書くか）
- 一次ソースURL
- 媒体（note / X）
- 検証済み事実のサマリー

### 1-2. エンティティ生成

読者（ミサキ層）のこの記事に対する心理・状況を具体化する。

```yaml
entity:
  who: "25歳マーケ職。Excel日報を毎日30分かけて作っている"
  pain: "AIで楽にしたいけど、何から手をつけていいかわからない"
  trigger: "同僚が『ChatGPTで日報5分になった』と言っていた"
  fear: "難しそう。プログラミングが必要だったら無理"
  hope: "コピペだけでできるなら今日やりたい"
```

`knowledge/account-concept.md` のミサキ層定義を参照。

### 1-3. 読者価値の定義

この記事を読んだ読者が得る具体的な価値を定義する。

```yaml
reader_value:
  functional: "ChatGPTでExcel作業を自動化する手順がわかる"
  emotional: "自分にもできそう、という自信"
  social: "同僚に教えられる立場になれる"
  action: "今日の帰りに試せる3ステップ"
```

### 1-4. ブランド変容設計

読後に、このアカウントに対するイメージがどう変わるかを設計する。

```yaml
brand_shift:
  before: "AIの情報を発信してるアカウントらしい"
  after: "画面付きで正直に見せてくれる。信頼できる"
  key_moment: "制限事項を隠さず書いている箇所で信頼が跳ねる"
```

### 1-5. C×P選択 + スキル検索

`knowledge/content-types.md` を参照し、エンティティと価値定義に最適な C×P を選択。
SKILL.md の「C×P別スキル選択表」からスキルセットを特定する。

```yaml
content_design:
  type: "C3 × P4"
  media: "note"
  skills_c: ["headline-writing", "hook-creation", "trust-building"]
  skills_p: ["headline-writing", "hook-creation"]  # 重複は除去
  skills_media: ["paragraph-design"]
  演出:
    掛け合い: "導入で1回（3往復以内）"
    実画面: "あり（実演判定OK）"
    図解: "変更点の可視化に1枚"
```

### 1-6. アウトライン構造作成（メイン）

content-types.md の骨格テンプレートに沿って**構造とセクションの役割**を組む。
見出しの文言は仮置きでよい（見出しAgentが最終調整する）。

```markdown
## アウトライン構造

### セクション構成
- リード: [全結論。何がわかるか + 誰向けか]
- H2-1: [セクションの役割と入れる情報]
- H2-2: [セクションの役割と入れる情報]
- ...
- 参考: [公式ソースのみ]

### 各セクションの役割
- リード → NOT Read 突破（hook-creation）
- H2-1 → 事実提示（trust-building）
- H2-3 → 差別化ポイント（実画面武器化）
- H2-5 → NOT Believe 突破（制限も書く）
```

### 1-7. 見出し作成（サブエージェント）

アウトライン構造を見出しAgentに渡し、タイトルとH2見出しを作成させる。

#### 見出しAgentプロンプトテンプレート

```
あなたは見出し専門のコピーライターです。
以下のアウトライン構造に対して、タイトルとH2見出しを作成してください。

## 読むべきファイル
- {SKILL_DIR}/headline-writing.md
- {SKILL_DIR}/benefit-writing.md
- {KNOWLEDGE_DIR}/account-concept.md

## エンティティ
{ENTITY_YAML}

## アウトライン構造
{OUTLINE_STRUCTURE}

## 見出しルール
- タイトル: 28〜32文字。10案以上出し、3案に絞る
- 【】フックはタイトルか最初のH2の1箇所のみ。全見出しに入れない
- H2: 情報が一目でわかる素直な一文。ダッシュ（—）は使わない
- 制限・ネガティブ情報は読者の欲求に変換する
- 驚き屋ワード禁止（やばい、神、革命、衝撃）
- ミサキ層が「自分に関係ある」と思える言葉を使う
- ベネフィットか読者の言葉を含む

## 出力形式

### タイトル候補（3案）
1. ...
2. ...
3. ...

### H2見出し
| # | 見出し |
|---|--------|
| H2-1 | ... |
| H2-2 | ... |
| ... | ... |
```

#### 見出しAgentのスキルローディング

| スキル | 役割 |
|--------|------|
| **headline-writing.md** | タイトル・H2の設計技法 |
| **benefit-writing.md** | 機能→ベネフィット変換 |
| `knowledge/account-concept.md` | ミサキ層の言葉・NGトーン |

### 1-8. レギュレーション確認

`quality-standards.md` のチェックリストでアウトラインを事前検証。

- [ ] 目的の階層（L1〜L5）が定義されているか
- [ ] エンティティに合った語彙レベルか
- [ ] 驚き屋ワードが入っていないか
- [ ] 結論がリードに入っているか
- [ ] 参考リンクは公式ソースのみか

### 1-8. ユーザー承認ゲート

アウトライン + エンティティ + 価値定義 + ブランド変容をユーザーに提示。
**承認を得てから Phase 2 に進む。**

---

## Phase 2: 執筆（サブエージェント）

### 執筆Agentプロンプトテンプレート

```
あなたは note/X 記事の執筆者です。以下のアウトラインに従って本文を生成してください。

## 読むべきファイル（必ず全て Read してから執筆開始）

### Base スキル（絶対）
- {SKILL_DIR}/SKILL.md
- {SKILL_DIR}/quality-standards.md
- {SKILL_DIR}/three-nots.md
- {SKILL_DIR}/reader-adaptation.md
- {SKILL_DIR}/sentence-construction.md
- {SKILL_DIR}/concise-writing.md

### ナレッジ
- {KNOWLEDGE_DIR}/content-types.md
- {KNOWLEDGE_DIR}/account-concept.md
- {KNOWLEDGE_DIR}/characters/team-orchestra.md（掛け合いがある場合）

### C×P×媒体別スキル
{RESOLVED_SKILLS}

## エンティティ（この読者のために書く）
{ENTITY_YAML}

## 読者が得る価値
{READER_VALUE_YAML}

## ブランド変容（読後にこう思わせる）
{BRAND_SHIFT_YAML}

## アウトライン
{OUTLINE}

## 執筆ルール
- アウトラインの構造を変えない。肉付けのみ
- 一文60文字以内（掛け合い30文字以内）
- **レギュレーション正本は `quality-standards.md` の「共通レギュレーション」「note記事レギュレーション」「X投稿レギュレーション」に従うこと**（一次解釈の原則、トーン、媒体別ルールはすべてそちらに記載）

## 出力形式
note記事の場合: noteエディタに貼れるプレーンテキスト形式（Markdown見出しOK）
X投稿の場合: 本文テキスト + 画像指示（あれば）
```

### 変数解決

| 変数 | 解決方法 |
|------|---------|
| `{SKILL_DIR}` | `.agent/skills/god-writing` の絶対パス |
| `{KNOWLEDGE_DIR}` | `knowledge` の絶対パス |
| `{RESOLVED_SKILLS}` | Phase 1-5 で特定したスキルファイルの絶対パスリスト |
| `{ENTITY_YAML}` | Phase 1-2 の出力 |
| `{READER_VALUE_YAML}` | Phase 1-3 の出力 |
| `{BRAND_SHIFT_YAML}` | Phase 1-4 の出力 |
| `{OUTLINE}` | Phase 1-6 の出力 |

---

## Phase 3: 校正（サブエージェント）

### 校正Agentプロンプトテンプレート

```
あなたは note/X 記事の校正者です。以下の原稿を校正し、品質判定してください。

## 読むべきファイル（必ず全て Read してから校正開始）
- {SKILL_DIR}/quality-standards.md
- {SKILL_DIR}/proofreading.md
- {SKILL_DIR}/emphasis-technique.md
- {KNOWLEDGE_DIR}/account-concept.md

## 校正対象
{DRAFT_TEXT}

## エンティティ（この読者基準で判定）
{ENTITY_YAML}

## ブランド変容（この変容が起きるか確認）
{BRAND_SHIFT_YAML}

## 校正ルール

### 表記チェック
- 数字: 算用数字（1, 2, 3）
- AI名: 公式表記（ChatGPT, Claude, Gemini）
- こと/とき/もの: ひらがな
- ですます調の統一

### 品質判定（5軸 × 5段階）
以下の5軸それぞれに Level を付ける。全軸 Level 4 以上が合格。

1. 目的達成度
2. 読者適合度
3. 論理構造
4. 表現品質
5. 信頼性

### 3NOT チェック
- NOT Read: タイトルで止まるか / リード3行で全結論 / 図解で崩しているか
- NOT Believe: 一次ソース / 実画面 or 具体結果 / 制限を隠していないか
- NOT Act: 今日やれること / 3ステップ以内 / 「やってみよう」で着地

### 驚き屋チェック
account-concept.md の NGワード・NGトーンに抵触していないか

## 出力形式

### 判定
- 合格 / 差し戻し（Level 3以下の軸を明記）

### 5軸スコア
| 軸 | Level | コメント |
|---|---|---|

### 修正リスト（差し戻し時）
| # | 箇所 | 問題 | 修正案 |
|---|---|---|---|

### 修正済み原稿（差し戻し時）
修正を適用した全文を出力
```

---

## Phase 3.5: 文字数プリフライトチェック

校正合格後、公開タスクに渡す前に文字数制限を確認する。
制限値は `config/platforms.yaml` の `char_limits` を正とする。

### チェック項目

| 媒体 | フィールド | 制限 | 超過時の対応 |
|------|-----------|------|-------------|
| note | 記事タイトル | 80文字 | タイトルを短縮 |
| X | ポスト本文 | 140文字（プレミアムなし） | 本文を分割 or 短縮 |
| X | ポスト本文 | 25,000文字（プレミアム） | 通常は問題なし |

### 実行手順

1. 校正合格した最終原稿からタイトル・本文を抽出
2. 各フィールドの文字数をカウント（改行・スペース含む）
3. 制限超過があれば、校正Agentに差し戻して短縮を依頼
4. 全フィールドが制限内であることを確認してから Phase 4 へ

### X ポスト向け追加チェック

- URLは23文字として計算（X の t.co 短縮）
- ハッシュタグは `#` 含む文字数でカウント
- 画像添付時もURLカウントに影響しない（X仕様）

---

## Phase 4: 完了処理

### 校正合格時

1. 最終原稿をユーザーに提示
2. ユーザー承認後、媒体に応じた公開タスクへ引き渡す

```
# note 記事
/run-task note-article-publish

# X 投稿
/run-task x-post-publish
# または
/run-task x-idea-post-publish
```

### note記事投稿の実証済みルート（2026-03-12）

エディタでの操作順序が確立済み。タスクYAML（`note-article-publish.yaml`）に反映済み。

```
1. サムネイルアップ → 2. タイトル入力 → 3. 本文DOM一括操作
→ 4. 画像挿入（位置ごと） → 5. 太字バッチ処理
→ 6. 目次挿入（見出し確定後） → 7. 公開に進む
→ 8. ハッシュタグ追加（slowly combobox） → 9. 設定確認
→ 10. 投稿 → 11. スキ設定 → 12. 公開確認
```

**key insight**: 本文はbrowser_typeの繰り返しよりDOM一括操作（browser_evaluate）が圧倒的に速い。太字も一括バッチ。

### 校正差し戻し時

1. 修正リストを確認
2. 差し戻し理由が Level 3 の軸を特定
3. 執筆Agent を再ディスパッチ（修正指示 + 修正済み原稿を入力に含める）
4. 再校正

**差し戻しは最大2回。** 2回で Level 4 に達しなければユーザーにエスカレーション。

---

## フロー全体図

```
/research → handoff
  ↓
/generate-content
  ↓
Phase 1: 戦略設計（メイン）
  1-1 入力確認
  1-2 エンティティ生成        ← account-concept.md
  1-3 読者価値の定義
  1-4 ブランド変容設計
  1-5 C×P選択 + スキル検索    ← content-types.md + SKILL.md
  1-6 アウトライン構造作成     ← content-types.md 骨格（見出しは仮置き）
  1-7 見出し作成              ← 見出しAgent（headline-writing + benefit-writing）
  1-8 レギュレーション確認     ← quality-standards.md
  1-9 ユーザー承認ゲート       ★ 人間確認
  ↓
Phase 2: 執筆（サブエージェント）
  Base 6スキル + C×P×媒体別スキル + ナレッジ
  → 本文生成
  ↓
Phase 3: 校正（サブエージェント）
  quality-standards + proofreading + emphasis-technique + account-concept
  → 品質判定
  ↓ (合格)          ↓ (差し戻し: 最大2回)
Phase 3.5: 文字数チェック → Phase 2 に戻る
  → config/platforms.yaml の char_limits で検証
  ↓ (OK)
Phase 4: 完了
  → ユーザー最終レビュー
  → /run-task で公開
```
