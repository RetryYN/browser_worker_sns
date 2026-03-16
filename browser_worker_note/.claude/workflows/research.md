---
description: ネタ調査から記事化・投稿候補の引き渡しまでを行うリサーチワークフロー
---

# /research ワークフロー

ネタの収集、分類、実演可否判断、検証、キュー登録、`/run-task` への引き渡しまでを担当する。

## 使い方

```
/research [任意のフォーカス]
```

例:
- `/research Claude Code`
- `/research AI画像生成のネタを3本`
- `/research X向けの参加型ネタを探す`

---

## このワークフローの責務

- 外部ソースからネタ候補を集める
- `update / compare / howto / trend / real` に分類する
- 実演できるか判定する
- 必要な事実確認をする
- リサーチログを更新する
- X向けなら `knowledge/x-content-queue.md` を更新する
- note/X に流すための handoff を作る

**やらないこと**
- その場で投稿・公開まではしない
- 課金・削除・設定変更はしない
- 実演のためだけに危険操作をしない

---

## 起動時に読むファイル

### 全モード共通（必須）

1. `knowledge/x-content-queue.md` — キュー状況（重複チェック用）
2. `config/policies.yaml` — 禁止事項
3. 当日ログ `knowledge/logs/research/YYYY-MM-DD.md`（なければ `_template.md` を複製して作成）

### 定期リサーチ・ディープリサーチで追加

4. `knowledge/account-concept.md` — ペルソナ・ポジショニング
5. `knowledge/external-sources.md` — 巡回先ソース一覧
6. `knowledge/content-types.md` — C×P選択基準
7. `.agent/skills/god-writing/quality-standards.md` — テーマ選定の原則
8. `knowledge/sites/x/posting-strategy.md` — 配置ルール

---

## 3つの実行モード

タスクの緊急度と深さに応じて、3モードから選択する。指定がなければ**クイック巡回**をデフォルトとする。

| モード | 目安時間 | 使うステップ | いつ使うか |
|--------|---------|------------|-----------|
| **クイック巡回** | 5分 | 1, 2, 3-1, 4, 11 | 毎日の定点チェック。inbox に候補を入れるだけ |
| **定期リサーチ** | 30分 | 1-4, 6-7, 9-11 | 週2-3回。ネタタイプ判定 + queue更新まで |
| **ディープリサーチ** | 1時間 | 全ステップ(1-12) | 記事化前提のテーマ深掘り。5軸分類 + handoff生成 |

### モード別の省略ルール

- **クイック巡回**: 5軸分類(Step 5)・実演判定(Step 7)・検証(Step 8) は省略。「ミサキ刺さり度」のみ判定
- **定期リサーチ**: 5軸分類は省略可。ネタタイプ + ミサキ刺さり度 + 実演判定の3軸で判断
- **ディープリサーチ**: 省略なし。5軸分類・検証・handoff生成まで完遂する

### クイック巡回の最小ログ

クイック巡回では、当日ログに以下のミニマムセットのみ記録すればよい:

```markdown
| タイトル | URL | ネタタイプ | ミサキ刺さり度 | 判定 |
|---------|-----|----------|-------------|------|
| ... | ... | update/trend/... | high/medium/low | keep/drop |
```

---

## 実行手順

### 1. スコープ確認

ユーザーの指示から以下を決める。

- 対象媒体: `note / x / both`
- 優先トピック: 例 `Claude`, `ChatGPT`, `AI比較`
- 本数目安: 指定がなければ **3候補**
- 緊急度: `速報系` か `ストック系` か

指定が曖昧なら、以下をデフォルトにする。

```yaml
target: both
count: 3
priority: balanced
```

### 2. 当日ログ準備

1. `knowledge/logs/research/_template.md` を読む
2. 当日ログ `knowledge/logs/research/YYYY-MM-DD.md` がなければ作成する
3. すでに同日ログがあれば追記モードで使う

### 3. 候補収集

#### 3-1. X Search によるトレンド収集（推奨）

フォーカスが指定されている場合、まず X Search で X 上のリアルタイムな話題を収集する。

```bash
# トレンド検索
python scripts/x_search.py trend "<フォーカスキーワード>" --period 7d

# 特定トピックの事前調査
python scripts/x_search.py topic "<候補テーマ>" --period 30d
```

- 結果は `knowledge/logs/x/research/trend/` に YAML 保存される
- ネタ候補は `knowledge/logs/x/research/ideas.yaml` に自動蓄積される
- 蓄積済みの ideas.yaml も確認し、未使用のネタがあればそこから拾う

#### 3-2. 外部ソース巡回

`knowledge/external-sources.md` のソースを WebSearch / WebFetch で確認する。
RSS/API 列が記載されているソースは WebFetch で効率的に取得可能。

収集項目:
- タイトル
- URL
- 公開日
- ソースカテゴリ

#### 3-3. ブラウザ巡回（WebFetch不可のソース）

WebFetch で取得できないサイトは Playwright で巡回する。

手順:
1. `browser_navigate`
2. `browser_snapshot`
3. 見出し一覧を取得
4. 最新ログとの差分を見る
5. 新着だけを候補に追加

### 4. 一次ふるい

各候補を以下で落とす。

- 明らかな二次転載のみ
- 既に同趣旨で直近対応済み
- 実読価値が薄い細かな UI 文言変更
- 安全に検証できない課金・削除・設定変更系

### 5. 情報の5軸分類

> **スキップ条件**: クイック巡回・定期リサーチでは省略可。ディープリサーチでのみ必須。

一次ふるいを通過した候補ごとに、情報を5つのベクトルで分類する。この分類が記事の切り口（T軸）と価値の源泉を決める。

```yaml
info_vectors:
  semantic: "この情報は何を意味するか（一文で）"
  awareness: "高/中/低 — ターゲット層がどれくらい知っているか"
  discovery: "調べて初めてわかった事実（なければ空）"
  forgotten: "かつて知られていたが忘れられている事実（なければ空）"
  psychological: "読者がこの情報に触れたときの感情（驚き/不安/期待/etc.）"
```

**分類例:**
```yaml
# 候補: Notion AIのモデル選定
info_vectors:
  semantic: "AIツールの裏で動くモデルは選択・切替の時代に入った"
  awareness: 低
  discovery: "OpenAIからAnthropicに主要モデルを切り替えていた"
  forgotten: "GPT-3は2020年から存在したが開発者しか使えなかった"
  psychological: "え、そうだったの？ → 他のツールも裏が違う？"
```

**5軸 → 記事価値の判定:**
- awareness 低 + discovery あり → **高価値**（読者の常識を覆せる）
- awareness 高 + discovery なし → **低価値**（周知の事実の繰り返し）
- forgotten あり → **中〜高価値**（歴史の掘り起こしで独自性）
- psychological が強い → **高価値**（感情が動く＝シェアされやすい）

**5軸 → T軸（加工方法）の推奨:**

`content-types.md` の「T の選び方（5軸ベクトルから）」を正本とする。

### 6. ネタタイプ判定

| タイプ | 判定基準 | 推奨 content-type |
|---|---|---|
| `update` | 新機能、仕様変更、リリース | `C3 × P4` または `C3 × P8` |
| `compare` | 複数AI・複数ツールの比較 | `C6 × P3` または `C6 × P8` |
| `howto` | 手順、ノウハウ、再現方法 | `C2 × P2` または `C2 × P6` |
| `trend` | 市場動向、数値、業界解説 | `C8 × P4` または `C8 × P1` |
| `real` | 実体験、あるある、運用知見 | `C4 × P6` または `C4 × P8` |

### 7. 実演判定

以下5項目を `OK / NG` で判定する。

1. ブラウザで到達可能か
2. 操作が再現可能か
3. スクショに意味があるか
4. 安全に実行可能か
5. ログイン済みセッションで到達可能か

判定ルール:
- `OK 5/5`: 実演あり
- `OK 3-4/5`: 部分実演
- `OK 0-2/5`: テキストのみ

### 8. 検証

検証対象:
- 機能
- 料金
- 数値
- 日付
- 比較軸

手順:
1. 記事化・投稿化に使う事実を抽出
2. 一次ソースを特定
3. 必要ならブラウザまたは WebSearch/WebFetch 相当で再確認
4. 未確認事項は留保表現前提で記録

### 9. 媒体ごとの落とし先を決める

以下の判定表で振り分ける。2項目以上該当した方に寄せる。両方2項目以上なら `both`。

#### note 判定（2項目以上で note 向き）

- [ ] 説明に500字以上必要（手順・背景・比較の深掘りがある）
- [ ] 実画面スクショ3枚以上で見せたい内容がある
- [ ] C×Pの骨格に自然にはまる（content-types.md参照）
- [ ] ストック型（1週間後に読んでも価値がある）

#### X 判定（2項目以上で X 向き）

- [ ] 結論が1文で言い切れる
- [ ] 画像1枚で伝わる（図解・比較表・スクショ）
- [ ] posting-strategy.md の10型のどれかにはまる
- [ ] フロー型（今日見ないと価値が下がる。速報・トレンド）

#### both 向き

- note: 詳細版（本体）
- X: note記事の核心を抜き出して転用（§11.5のマッピング参照）

### 10. ログ更新

当日ログに各候補を追記する。モードに応じて記録項目が異なる。

#### クイック巡回（最小セット）

| タイトル | URL | ネタタイプ | ミサキ刺さり度 | 判定 |
|---------|-----|----------|-------------|------|

#### 定期リサーチ

上記に加えて:
- ソースカテゴリ
- トピック
- 実演判定
- 推奨 `C × P`
- 一言要約

#### ディープリサーチ（フルセット）

上記に加えて:
- 5軸分類（`info_vectors` YAML）
- 推奨T（加工方法）
- 検証状態
- 推奨 `C × P × T`

### 11. キュー更新

#### 11-a. X キュー

X向き、または both 向きの候補は `knowledge/x-content-queue.md` に追記・更新する。

管理状態:
- `inbox`
- `ready`
- `scheduled`
- `posted`
- `dropped`

#### 11-b. note キュー

note向き、または both 向きの候補は `knowledge/note-content-queue.md` に追記・更新する。

管理状態:
- `Inbox` — 未検証のネタ
- `Ready` — リサーチ済み・検証済み。`/note-batch` で優先消費
- `Used` — 記事化済み
- `Dropped` — 見送り

**note キュー登録の基準:**
- 説明に500字以上必要
- 実画面スクショ3枚以上で見せたい内容がある
- C×Pの骨格に自然にはまる
- ストック型（1週間後に読んでも価値がある）

### 11.5. note→X転用チェック

note記事を公開済み or 下書き済みの場合、X投稿に転用できる要素がないか確認する。

**転用の手順:**
1. note記事の核心（結論・数値・図解）を抽出
2. 以下のマッピングで推奨Xパターンを決定
3. `x-content-queue.md` のReadyに追加

**ネタタイプ→Xパターン マッピング:**

| ネタタイプ | 推奨Xパターン | 転用のコツ |
|-----------|-------------|-----------|
| `update` | `trend-sokuhou` | 速報性が命。公開直後に投稿 |
| `compare` | `tsukaiwake-chart`, `dotchi-taiketsu` | 比較表を図解化。どっち派で参加誘発 |
| `howto` | `prompt-ba`, `tsukaiwake-chart` | Before/After or 手順を3行に凝縮 |
| `trend` | `trend-sokuhou`, `gachi-thread` | 数値フックで引く。深掘りはスレッド |
| `real` | `aruaru-kakeai`, `sankagata-odai` | 体験をあるある化。お題で読者参加 |

**重複防止チェック:**
- `x-content-queue.md` のPosted/Scheduledに同趣旨の投稿がないか確認
- 同じnote記事からの転用は最大2投稿まで（角度を変える）

### 12. handoff 生成

候補ごとに以下を出力する。

#### note handoff

```yaml
theme: "ネタタイトル"
source_url: "一次ソースURL"
content_type: "C3 × P4 × T7"
treatment: "対比（常識仮説 vs 事実のギャップ）"
info_vectors:
  semantic: "..."
  awareness: "低"
  discovery: "..."
  forgotten: ""
  psychological: "..."
topic_main: "Claude"
topic_sub: "AIニュース, Claude Code"
research_brief: "この記事で押さえるべき論点"
verification_log: "knowledge/logs/research/YYYY-MM-DD.md"
tags: "Claude, AIニュース, Claude Code"
```

#### X handoff

```yaml
theme: "ネタタイトル"
pattern: "quiz-senshuken / xgrid-4koma / tsukaiwake-chart / trend-sokuhou"
image_type: "quiz-choice / diagram / thumbnail / none"
source_url: "一次ソースURL"
fact_notes: "X本文で盛りすぎないための事実メモ"
verification_log: "knowledge/logs/research/YYYY-MM-DD.md"
```

#### 推奨コマンド

```text
# note 記事
/run-task note-article-publish theme: ... source_url: ... content_type: ... topic_main: ... topic_sub: ... research_brief: ... verification_log: ...

# X 投稿（軽量版 — 推奨）
/x-post <テーマ> schedule: YYYY-MM-DD HH:mm image: <image_type>

# X 投稿（/run-task 正式フロー）
/run-task x-idea-post-publish theme: ... pattern: ... image_type: ... source_url: ... fact_notes: ... schedule_at: ...
```

---

## 出力フォーマット

最終出力は以下の3部構成にする。

### 1. 今日の候補

3件前後。優先度順。

### 2. 推奨アクション

- note に回す候補
- X に回す候補
- 見送る候補

### 3. handoff

そのまま `/run-task` に渡せる形で提示する。

---

## パイプライン接続

```
/research → x-content-queue.md (Ready) → /x-post おまかせ → /x-batch
          → note-content-queue.md (Ready) → /generate-content → /note-batch
```

- **接続点はキューファイル**。handoff YAMLは参考情報であり、下流コマンドは直接読まない
- /research は候補をReadyに入れるところまで。投稿実行は下流コマンドに委任する
- X: `/x-post` または `/x-batch` で消費
- note: `/generate-content` または `/note-batch` で消費

---

## 運用ルール

- 同じ日付のログは新規作成せず追記する
- research ログの本文は事実と判断を分けて書く
- 検証未完了のネタを「確定ネタ」として queue に入れない
- X向け queue に入れる時は `posting-strategy.md` の10型を必ず1つ紐付ける
- 実演スクショがある場合は保存先も handoff に残す
- note 記事化時は `note-article-publish` に research 情報を引き継ぐ
