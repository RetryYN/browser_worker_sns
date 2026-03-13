---
description: タスクYAMLを読み込んでブラウザ操作を自動実行するメインワークフロー（Claude Code + Playwright MCP版）
---

# /run-task ワークフロー

タスクYAMLに定義されたステップを順次実行し、ブラウザ操作・文章生成を自動で行う。

## 使い方

```
/run-task <タスク名> [追加の指示]
```

例: `/run-task note-article-publish テーマ: AIエージェントの現在地`

---

## ツール対応表（Claude Code）

| アクション | 使用ツール |
|---|---|
| URL遷移 | `mcp__playwright__browser_navigate` |
| ページ構造取得 | `mcp__playwright__browser_snapshot` |
| クリック | `mcp__playwright__browser_click` |
| フォーム入力 | `mcp__playwright__browser_fill_form` |
| テキスト入力 | `mcp__playwright__browser_type` |
| キー操作 | `mcp__playwright__browser_press_key` |
| スクリーンショット | `mcp__playwright__browser_take_screenshot` |
| ファイルアップロード | `mcp__playwright__browser_file_upload` |
| JS実行 | `mcp__playwright__browser_evaluate` |
| コマンド実行 | `Bash` |
| ファイル読み書き | `Read` / `Write` / `Edit` |
| 文章生成 | Claude自身（スキル参照） |

---

## ステップ一覧

各フェーズが組み合わせるビルディングブロック。

| ステップ | Code | 名称 | 概要 |
|---------|------|------|------|
| A | Order | タスク指令 | ユーザー指示の受領・解析・権限確認 |
| B | Recon | 外部探索 | ファイルベースの情報収集（ブラウザ不使用） |
| C | Probe | 内部探索 | ブラウザ構造調査 + スキル・リソース読み込み |
| D | Map | マッピング | サイト構造の網羅的記録 |
| E | Observe | モニタリング | 操作対象の現在値・状態を記録（変更前スナップショット） |
| F | Plan | プランニング | 実行計画の組み立て・最適化 |
| G | Act | アクション | ワークフロー制御 + ブラウザ操作・テキスト生成の実行 |
| H | Review | レビュー | 生成物の品質確認・ユーザー承認 |
| I | Verify | チェック | 実行結果の検証・ナレッジ記録 |
| J | Report | レポーティング | 前回との差分比較・報告 |
| K | Offer | オファー | ユーザーへの成果報告 |

---

## タスクYAMLで使えるアクション一覧

タスクYAMLの `steps[].action` に指定可能な値と、対応するツール・パラメータ。

| action | 実行ステップ | 対応ツール | 主要パラメータ | 実績 |
|--------|------------|----------|--------------|------|
| `navigate` | G-2 | `browser_navigate` | `url` | X投稿で検証済み |
| `login` | G-3 | `browser_*` 複合 | `site` | X/noteで検証済み |
| `interact` | G-4 | `browser_*` 複合 | `description` | X投稿で検証済み |
| `verify` | G-5 | `browser_snapshot` + `browser_take_screenshot` | `description` | X投稿で検証済み |
| `generate_text` | G-6 | Claude自身 | `instruction`, `skill` | 未テスト（手動で同等実行） |
| `committee_review` | G-7 | Sub-agents | `target_text`, `review_pipeline`, `skill` | 未テスト（手動で同等実行） |
| `generate_image` | G-8 | `Bash` → `generate_image.py` | `type`, `prompt`, `topic`, `style`, `chars`, `layout`, `quiz_data` | 画像生成で検証済み |
| `upload_image` | G-9 | `browser_file_upload` | `file_path` | X投稿で検証済み |
| `command` | G-10 | `Bash` | `command` | 未テスト |

**条件付き実行**: `when` フィールドが空文字・false・none・null・skip なら `skipped`
**結果参照**: `{{prev_result}}`, `{{step_results[N]}}` で前ステップの出力を参照

---

## フェーズ定義

フェーズ = 実行パターン。状況に応じてステップを組み合わせる。

### フェーズ判定

```
Step B（外部探索）完了時:
  knowledge/sites/<site名>/ ディレクトリが存在しない？
    → YES: フェーズ① 初回
    → NO:
      knowledge/logs/ に同じタスクの成功ログがある？
        → NO: フェーズ② 再訪問
        → YES:
          過去ログに短縮メモがある？
            → YES: フェーズ④ 最適化
            → NO: フェーズ② 再訪問

※ フェーズ③ は Step C の照合で差異検出時に自動発動する
```

### フェーズ別ステップ構成

| フェーズ | ステップ構成 | 制約・特徴 |
|---------|-------------|-----------|
| ① 初回 | A → B → C → **D** → C → E → **F(確認)** → G → H → I → K | D 必須、F でユーザー確認必須、J なし |
| ② 再訪問 | A → B → C → E → **J** → F → G → H → I → K | D スキップ、J で前回差分を確認してから計画 |
| ③ 構造変更 | A → B → C → **D(更新)** → C → E → **J** → F → G → H → I → K | ②中に C で差異検出 → D 挿入 |
| ④ 最適化 | A → B → C → E → **J** → **F(短縮メモ適用)** → G → H → I → K | J で差分確認後、F で短縮メモ反映 |

### 組み合わせ制約

| 制約 | 内容 |
|------|------|
| A・B・C は全フェーズ必須 | 省略不可 |
| D はフェーズ①で必須 | ②④ではスキップ、③では差異検出時のみ挿入 |
| E は全フェーズ必須 | 変更前の状態記録は常に行う |
| F の確認はフェーズ①のみ | ②③④ではユーザー確認をスキップ |
| H は生成系タスクのみ | generate_text / committee_review がないタスクではスキップ |
| J はフェーズ②③④のみ、E の直後に実行 | 初回（①）は前回データがないためスキップ。操作前に前回差分を把握する |
| F の破壊的操作チェックは全フェーズ | 計画提示は①のみだが、破壊的操作の警告は省略不可 |
| G・I・K は全フェーズ必須 | 省略不可 |

### 実行チェックリスト

B-4（フェーズ判定）完了直後に、以下の形式で実行するステップを宣言する。各ステップ完了時に更新して出力する。

```
【実行チェックリスト】フェーズ②再訪問
- [x] A. タスク指令
- [x] B. 外部探索 → フェーズ②判定
- [ ] C. 内部探索
- [ ] E. モニタリング
- [ ] J. レポーティング
- [ ] F. プランニング（計画提示スキップ、破壊的操作チェックあり）
- [ ] G. アクション
- [ ] H. レビュー ← 生成系のため実行
- [ ] I. チェック
- [ ] K. オファー
```

**チェックリストのルール:**
- フェーズ判定後、該当フェーズのステップ構成に従って一覧を生成する
- 該当フェーズで実行しないステップは一覧に含めない
- 条件付きステップには理由を注記する（例: `← 生成系のため実行`）
- 各ステップ完了時に `[x]` に更新し、ユーザーに進捗を示す
- **フェーズ③発動時**: C-4 で差異検出されフェーズ③に切り替わった場合、チェックリストを再生成する（D を挿入し、フェーズ表記を③に更新）

---

## Step A. タスク指令

ユーザーの指示を受け取り、実行可能な状態にする。

### A-1. ポリシーチェック

1. ユーザーの指示内容を `policies.yaml` の `forbidden_actions` と照合する
2. **禁止に該当**: 「この操作はできません。理由: [message]」→ **停止**
3. **確認が必要** (`require_confirmation_before`): ユーザーに確認を求める
4. **問題なし**: 次へ

### A-2. タスクYAML読み込み

1. `tasks/<タスク名>.yaml` を Read で読み込む
2. タスクが見つからない場合、`tasks/` を Glob で一覧表示して候補を提示する
3. タスクの `params` を確認し、ユーザーの指示から値を抽出する
4. 不足パラメータがあればユーザーに質問する
5. タスクのルート情報 (`task_name`, `site`, `params`) をテンプレートコンテキストとして保持する。**required: false の未指定パラメータは空文字として初期化する**
6. 各ステップ実行直前に、**そのステップ配下のすべての文字列フィールド**に対して `{{...}}` を再解決する
7. 解決対象は `description`, `instruction`, `target_text`, `site`, `url`, `prompt`, `topic`, `style`, `chars`, `story`, `layout`, `quiz_data`, `file_path`, `command` などの文字列値全般とする
8. 使える変数は `{{site}}`, `{{param_name}}`, `{{prev_result}}`, `{{step_results[N]}}`
9. ステップに `when` がある場合は、その値もテンプレート解決する。解決後の値が空文字、`false`, `0`, `none`, `null`, `skip` のいずれかなら、そのステップは `skipped` として記録し次へ進む
10. **required: true の未指定パラメータ**、または未知の変数名で解決不能な変数が残る場合、そのステップは実行せず不足情報を確認する

### A-3. 指令サマリー生成

抽出した情報を整理し、以降のステップで参照する。

```
task_context = {
  task_name: <タスク名>,
  site: <対象サイト>,
  params: { key: value, ... },
  steps_count: <ステップ数>,
  has_destructive_action: true/false,
  has_generation: true/false
}
```

---

## Step B. 外部探索

ブラウザを開く前に、ファイルベースで情報を収集する。

### B-1. サイト情報取得

1. `config/sites.yaml` を Read で読み込む
2. `task_context.site` に対応するサイト情報（URL、ログインURL、認証方式等）を取得する

### B-2. サイトナレッジ読み込み

1. `knowledge/sites/<site名>/` ディレクトリの存在を Glob で確認する
2. **存在する場合**: `index.md` を Read で読み込み、概要・ナビゲーション・注意点を把握する。タスク対象に応じて個別ファイル（`article-editor.md` 等）も Read する
3. **存在しない場合**: 初回ターンと判定。マッピングステップが必要

### B-3. 過去ログ確認

1. `knowledge/logs/` で同じタスクの過去ログを Glob で検索する
2. **ログあり**: Read で読み込み、前回の実行ステップ・学び・エラー・短縮メモを把握する
3. **ログなし**: 初回実行と判定

### B-4. フェーズ判定・チェックリスト生成

1. B-2・B-3 の結果から実行フェーズ（①〜④）を決定する
2. フェーズ別ステップ構成と組み合わせ制約に従い、実行チェックリストを生成してユーザーに出力する

---

## Step C. 内部探索

ブラウザを起動してページ構造を調査し、タスクに必要なスキル・リソースを読み込む。

### C-1. ブラウザ起動

1. `mcp__playwright__browser_navigate` でサイトURLにアクセスする
2. `mcp__playwright__browser_snapshot` でページを確認する

### C-2. ログイン（必要な場合のみ）

1. `mcp__playwright__browser_snapshot` でログイン状態を確認する
2. **未ログインの場合**: `config/sites.yaml` からログインURLを取得し `mcp__playwright__browser_navigate` で遷移する
3. ログインフォームに `mcp__playwright__browser_fill_form` または `mcp__playwright__browser_type` で認証情報を入力し、ログインを実行する
4. `mcp__playwright__browser_snapshot` でログイン成功を確認する。失敗時はリトライ（最大2回）
5. ログイン不要のタスクはこの手順をスキップする

### C-3. ページ構造取得

1. タスクの最初の操作対象ページに `mcp__playwright__browser_navigate` で遷移する
2. `mcp__playwright__browser_snapshot` でページ全体の構造を取得する

### C-4. マッピング照合

1. `knowledge/sites/` のマッピング情報と取得した構造を比較する
   - **一致** → C-5 へ進行
   - **差異あり** → **Step D（マッピング）に遷移**し、差異箇所を更新してから C-3 に戻る（→ フェーズ③発動）
   - **マッピングなし**（フェーズ①）→ **Step D（マッピング）に遷移**

### C-5. スキル・リソース読み込み（生成系タスクの場合）

`task_context.has_generation` が true の場合のみ実行する。

1. タスク全体ではなく、**各生成系ステップ**（`generate_text`, `committee_review`, `generate_image`）の `skill` 指定を確認し、必要な `.agent/skills/<skill>/SKILL.md` だけを Read で読み込む
2. SKILL.md 内の依存ファイル・必須参照リソースに記載されたファイルを Read で読み込む
3. `reference` が指定されている場合、対応するリソースファイルも Read で読み込む
4. `committee_review` がある場合は `config/personas.yaml` を Read で読み込む

### C-6. タスクターゲット特定

1. タスクYAMLの各ステップで操作するUI要素（ref）を特定する
2. 対象が見つからない場合: ページ内検索、メニュー探索、スクロールで探す
3. それでも見つからない場合: ユーザーに状況を報告し指示を仰ぐ
4. 構造情報を `page_context` として保持し、以降のステップで参照する

---

## Step D. マッピング

サイト全体の構造を網羅的に探索し、ナレッジとして永続化する。
Step C（C-4）から遷移した場合のみ実行する。

### D-1. ファーストアタック（内部監査 — 管理画面探索）

ログイン後の管理画面を網羅的に探索する。目的: **自社が何を操作・確認できるか** の全体像を把握。

1. トップページ（またはダッシュボード）で `mcp__playwright__browser_evaluate` を実行し、ページ内の全リンクを一括抽出する:
   ```javascript
   () => [...document.querySelectorAll('a[href]')].map(a => ({
     text: a.innerText.trim().slice(0,60),
     href: a.href
   })).filter(l => l.href && !l.href.startsWith('javascript:'))
   ```
   これにより1回のアクションでサイト内の全ページ候補を網羅できる。
   **注意**: `textContent` ではなく `innerText` を使用する。`textContent` は CSS visibility:hidden の要素も含むため空文字になる場合がある。
2. 抽出したリンク一覧から **ページ全体像（サイトマップ）** を作成し、`index.md` に記録する
3. 補助的に `sitemap.xml` や `robots.txt` があればアクセスして参照する
4. グローバルナビ・サイドメニューの構成を把握する（主要メニュー項目とリンク先）
5. 各ページに順次遷移し、snapshot を取得する。**全ページを探索する** — タスクに関連するページだけでなく、サイト内のすべてのページを対象にする
6. ファーストアタック完了後、D-1b に進む

### D-1b. セカンドアタック（読者視点監査 — 公開ページ探索）

ログイン不要の公開ページを読者の視点で探索する。目的: **自社のコンテンツが読者にどう見えるか** を把握。

1. **自社公開ページ**: 公開プロフィール・記事一覧を読者視点で確認する
   - プロフィールの充実度（自己紹介、アイコン、ヘッダー画像）
   - 記事一覧の見え方（タイトル、サムネイル、スキ数）
   - 読者の導線（プロフィール -> 記事 -> フォロー）
2. 確認結果は `knowledge/sites/<site名>/public-page.md` に記録する

**SA 完了条件:**
- [ ] 公開プロフィール確認
- [ ] 記事一覧の表示確認
- [ ] `public-page.md` 作成

**2段階の関係:**
- **ファーストアタック（FA）**: 管理画面で何ができるかを把握する
- **セカンドアタック（SA）**: 読者に何が見えているかを把握する

### D-2. 構造記録

`knowledge/sites/<site名>/` ディレクトリに以下のファイル構成で記録する:

```
knowledge/sites/<site名>/
├── index.md          ← 基本情報・ログイン・ナビゲーション・探索状況・注意事項
├── <page-a>.md       ← 主要ページごとのフォーム構造・操作手順
├── <page-b>.md       ← 同上
└── ...
```

**ファイル分割ルール:**
- `index.md`（必須）: サイト概要、ナビゲーション構造、他ファイルへのリンク一覧、探索状況チェックリスト、注意事項
- 個別ページファイル（任意）: タスクで操作する主要画面ごとに1ファイル。ファイル名はページの役割を英語ケバブケースで（例: `article-editor.md`, `dashboard.md`, `post-composer.md`）
- 1ファイルが150行を超えたら分割を検討する

**各ファイルに記録する内容:**
- ページのURL パターン
- フォーム・テーブル・ボタンのレイアウトとフィールド一覧
- ページ遷移パターン（一覧→詳細→編集→確認→完了 等）
- 要注意要素（モーダル、非同期読み込み、iframe、確認ダイアログ等）
- 主要なref値とその役割

**必須記録ページ（該当する場合）:**

| ページ種別 | ファイル名例 | 記録する内容 |
|-----------|-------------|-------------|
| 記事エディタ | `article-editor.md` | エディタのUI構造、入力フィールド、公開フロー |
| ダッシュボード | `dashboard.md` | 取得可能な指標（PV、スキ、フォロワー等） |
| 投稿コンポーザー | `post-composer.md` | 投稿UI、文字数制限、添付機能 |

### D-3. マッピング完成度チェック

`index.md` にページ全体像（D-1 で抽出したリンク一覧）と探索状況チェックリストを記録し、完成度を算出する。

**完成度の定義:**
```
完成度 = 探索済みページ数 / サイト内総ページ数 × 100%
```

- **サイト内総ページ数**: D-1 で抽出したリンク一覧からユニークなページパス（クエリ・フラグメント除去、同一パターンの動的ページは1つとカウント）の数
- **探索済み**: そのページに遷移して snapshot を取得し、構造を `knowledge/sites/<site名>/` のいずれかのファイルに記録した状態

**`index.md` に記録するフォーマット:**
```markdown
## 探索状況

FA: ✅100% (8/8) ｜ SA: ✅完了 (2/2)

### ファーストアタック（管理画面）

| # | ページ | URL | 状態 | ナレッジファイル |
|---|--------|-----|------|----------------|
| 1 | ダッシュボード | /dashboard | ✅ 完了 | dashboard.md |
| 2 | 記事エディタ | /editor | ❌ 未探索 | — |
| 3 | 記事一覧 | /articles | ✅ 完了 | articles.md |
...

### セカンドアタック（公開ページ）

| # | ページ | URL | 状態 | ナレッジファイル |
|---|--------|-----|------|----------------|
| 1 | 公開プロフィール | /username | ✅ 完了 | public-page.md |
...
```

**ダッシュボード作成ゲート:**
- 完成度が **95% 未満** の場合、ダッシュボード（`knowledge/data/dashboard.html`）への新規メディア追加・タブ追加は **禁止**
- 95% 以上に達した時点で初めてダッシュボード作成に着手できる
- 既存ダッシュボードの軽微な修正（バグ修正、表記修正）はこの制限の対象外

### D-4. 内部探索に復帰

マッピング完了後、Step C の C-3 に戻る。

---

## Step E. モニタリング

操作対象の現在の状態を記録する。変更前のスナップショットとして保持し、チェック・レポーティングで比較基準にする。

### E-1. 現在値キャプチャ

1. 操作対象のページで `mcp__playwright__browser_snapshot` を実行する
2. タスクが変更する予定のフィールド・要素の**現在値**を抽出する
   - フォームの入力値（タイトル、タグ 等）
   - テキストコンテンツ（記事本文、投稿テキスト 等）
   - 選択状態（ドロップダウン、チェックボックス、ラジオボタン 等）
   - リスト・テーブルの件数や表示内容

### E-2. Before State 記録

キャプチャした現在値を `before_state` として保持する。

```
before_state = {
  captured_at: <タイムスタンプ>,
  page_url: <現在のURL>,
  fields: {
    <フィールド名>: <現在値>,
    ...
  },
  content: {
    <コンテンツ名>: <現在のテキスト>,
    ...
  }
}
```

---

## Step F. プランニング

収集した情報を元に、具体的な実行計画を組み立てる。

### F-1. 実行計画リファイン

1. タスクYAMLの各ステップを、特定済みのref値・ページ遷移パターンと紐付ける
2. **フェーズ④**: 過去ログの短縮メモを適用し、不要なステップを省く
3. **それ以外**: マッピング情報から最適なルートを組み立てる

### F-2. 実行計画の提示（フェーズ①のみ）

フェーズ②③④では計画の提示をスキップする。ただし F-3 の破壊的操作チェックは全フェーズで実行する。

1. 以下の形式で実行計画を提示する:
   ```
   【実行計画】
   対象サイト: <site名>
   対象ページ: <URL / ページ名>
   現在値: <before_state から主要項目を抜粋>
   操作内容:
     1. <操作の要約>（例: 「タイトルを入力し、本文をエディタに貼り付ける」）
     2. <操作の要約>
     ...
   変更されるデータ: <変更前 → 変更後>
   ```
2. ユーザーの承認を待つ。修正指示があれば内容を調整する

### F-3. 破壊的操作チェック（全フェーズ）

`task_context.has_destructive_action` が true の場合、フェーズに関わらず実行する。

1. 「この操作には **[投稿/削除/公開]** が含まれます。実行してよろしいですか？」
2. ユーザーの承認を待つ。拒否された場合はタスクを中断する

---

## Step G. アクション

タスクYAMLのステップを順次実行する。ワークフロー制御（データ受け渡し・ループ管理）もこのステップに含む。

### G-1. ワークフロー制御

各タスクステップの実行結果は `step_results` として蓄積する。後続ステップで `{{prev_result}}` や `{{step_results[N]}}` として参照可能。

```
step_results = []

ステップ1実行 → 結果を step_results[0] に格納
ステップ2実行 → {{prev_result}} は step_results[0] を参照
ステップ3実行 → {{prev_result}} は step_results[1] を参照
```

Claude は各ステップ実行前に、そのステップ配下のすべての文字列フィールドへテンプレート解決を適用する。`{{prev_result}}` は直前ステップの結果、`{{step_results[N]}}` は指定インデックスの結果を参照する。

`when` がある場合は、解決後の値で実行可否を判定する。空文字、`false`, `0`, `none`, `null`, `skip` は偽として扱い、そのステップを `skipped` にする。

```
resolved_step = resolve_templates(raw_step, {
  task_name,
  site,
  params,
  prev_result,
  step_results
})
```

タスクYAMLの `steps` を **上から順番に** 実行し、各ステップで `action` の種類に応じて以下の処理を行い、結果を `step_results` に記録する。

**生成→投稿の中断ルール:** generate_text / committee_review の直後に interact（投稿・入力）が続く場合、生成完了時点で Step H（レビュー）に遷移する。レビュー承認後に G に戻り、後続の interact を実行する。

### G-2. action: navigate

1. `mcp__playwright__browser_navigate` でURLにアクセスする
2. `mcp__playwright__browser_snapshot` でページ構造を確認する
3. ナレッジにページ構造の情報があれば参考にする

### G-3. action: login

> **通常は C-2 で実施済み。** タスク途中で別サイトへのログインが必要な場合のみ使用する。

1. `config/sites.yaml` から該当サイトのログインURLを取得
2. `mcp__playwright__browser_navigate` でログインページにアクセスする
3. ユーザーにログインを依頼し、完了を待つ
4. `mcp__playwright__browser_snapshot` でログイン状態を確認する

### G-4. action: interact

1. `mcp__playwright__browser_snapshot` で現在のページ構造を確認
2. `description` に記述された操作を、snapshot の ref を使って実行する
3. パラメータの `{{変数名}}` はユーザーの指示から抽出した値で置換する
4. `policies.yaml` の `forbidden_actions` に該当しないことを確認してから操作する
5. 操作結果を `step_results` に記録する

**ブラウザ操作の共通パターン**
`browser_type` がタイムアウトする textarea 等のワークアラウンドは `knowledge/sites/common/browser-patterns.md` を参照。
noteの記事エディタは `contenteditable` ベースのブロックエディタであり、通常の `fill_form` では入力できない場合がある。詳細はサイトナレッジ（`knowledge/sites/note/`）を参照。

### G-5. action: verify

1. `mcp__playwright__browser_snapshot` で結果を確認する
2. `mcp__playwright__browser_take_screenshot` でスクリーンショットを撮る
3. 期待した状態になっているか確認し、結果を `step_results` に記録する

### G-6. action: generate_text

1. Step C（C-5）で読み込み済みのスキル・リソースを参照する
2. `instruction` に従ってClaude自身がテキストを生成する
3. `instruction` が `TITLE:` や `BODY:` のような構造化フォーマットを要求している場合は、その見出しと順序を崩さずに出力する
4. 生成結果を `step_results` に格納して次のステップへ

### G-7. action: committee_review（組織的監査）

1. Step C（C-5）で読み込み済みの `personas.yaml` とスキルを参照する。`target_text` が未指定なら `{{prev_result}}` を対象にする
2. **Phase 1: 上流監査 (Upstream)**
   - `review_pipeline.upstream` で定義されたロールごとに、personas.yaml の **Upstream** 基準を適用
   - 各ロールが独立してテキストを検証し、ガイドラインや制約事項を出力する
   - 例: Editor(Upstream) → 「発信テーマがブランド方針に合っているか」を検証
   - 例: Marketer(Upstream) → 「ターゲット層に刺さる切り口か」を検証
3. **Phase 2: 下流修正 (Downstream)**
   - `review_pipeline.downstream` で定義されたロールごとに、personas.yaml の **Downstream** 基準を適用
   - Phase 1 で出た制約を守りつつ、実務視点でテキストを具体的に修正・再構築する
   - ロールに `skill` が指定されていれば、そのスキルの SKILL.md も参照して適用
   - 例: Writer(Downstream, skill: god-writing) → god-writing スキルで文章のリズム・読みやすさを改善
4. **Phase 3: 最終承認 (Executor)**
   - `executor` ロール（通常 CEO）の personas.yaml **Executor** 基準で最終判断
   - 各部門の意見が対立した場合、企業のビジョン・ミッションに最も合致する選択をする
5. 構造化テキストを受け取った場合は、その見出し（例: `TITLE:`, `BODY:`, `TAGS:`）を維持したまま最終成果物を `step_results` に格納する

### G-8. action: generate_image

Claude Code では画像生成を直接行わず、`Bash` 経由で `scripts/generate_image.py` を実行する。

1. Step C（C-5）で `image-generation` スキルと依存ファイルを読み込む
2. `type`, `prompt`, `topic`, `style`, `chars`, `story`, `layout`, `quiz_data` をテンプレート解決したうえで CLI 引数へ変換する
3. `Bash` で以下の形で実行する:
   ```bash
   python scripts/generate_image.py <type> "<prompt>" [--topic ...] [--style ...] [--chars ...] [--story ...] [--layout ...] [--quiz-data ...]
   ```
4. `OPENAI_API_KEY` や依存ファイルが不足している場合は、その時点で停止してユーザーへ不足条件を伝える
5. スクリプトの最終出力から生成ファイルパスを取得し、その**ローカルパス文字列**を `step_results` に保存する
6. 同一タスク内の後続 `upload_image` は、`file_path` が未指定ならこの `prev_result` を使ってよい

### G-9. action: upload_image

1. `file_path` が指定されていればそれを使う。未指定なら `{{prev_result}}` が既存ファイルパスか確認し、使える場合はそれを使う
2. `file_path` が空文字・未指定・存在しない場合は、このステップを `skipped` として記録して次へ進む
3. 投稿レイヤーでは画像のトリミング・リサイズ・縦横判定は行わない。生成レイヤーで用意されたファイルを**そのまま**扱う
4. `mcp__playwright__browser_file_upload` で画像ファイルをアップロードする
5. `mcp__playwright__browser_snapshot` でアップロード結果を確認する

### G-10. action: command

1. `Bash` で指定のコマンドを実行する
2. 出力を `step_results` に記録する

---

## Step H. レビュー

生成されたテキスト・コンテンツの品質を確認してから次の操作に進む。
generate_text / committee_review を含むタスクでのみ実行する。ブラウザ操作のみのタスクはスキップ。

### H-1. 生成物の提示

1. Step G で生成されたテキストをユーザーに提示する
2. 提示フォーマット:
   ```
   【生成結果】
   スキル: <使用したスキル名>
   用途: <どこに投稿/入力するか>
   ---
   <生成テキスト本文>
   ---
   ```

### H-2. ユーザー承認

1. ユーザーの判断を待つ:
   - **OK** → 生成物を確定し、後続のinteract操作で使用する
   - **修正指示** → 指示に従って再生成し、再度提示する
   - **却下** → タスクを中断し、理由をナレッジに記録する
2. committee_review の場合、Executor（CEO）の最終判断結果もあわせて提示する

### H-3. 投稿前最終確認

生成物をサイトに投稿・公開する直前に、以下を確認する:

1. 投稿先のフィールドと生成物の対応が正しいか
3. 「この内容で **[投稿/公開]** します。よろしいですか？」→ ユーザー最終承認

---

## Step I. チェック

実行結果を検証し、ナレッジを記録する。

### I-1. 結果検証

1. 最終ステップの `step_results` を確認し、全ステップが期待通りに完了したか判定する
2. 失敗したステップがあれば、エラー処理に従う

### I-2. After State キャプチャ

1. 操作対象のページで `mcp__playwright__browser_snapshot` を実行する
2. Step E で記録した `before_state` と同じフィールドの**変更後の値**を取得する
3. `after_state` として記録する

### I-3. タスク実行ログ記録

`knowledge/logs/<タスク名>_<YYYY-MM-DD>_<HHmm>.md` に以下を Write で記録する:

```markdown
# <タスク名> - <日付>
## 実行結果: 成功 / 失敗
## フェーズ: ①初回 / ②再訪問 / ③構造変更 / ④最適化
## パラメータ
- param1: value1
## Before State
- field1: <変更前の値>
- field2: <変更前の値>
## After State
- field1: <変更後の値>
- field2: <変更後の値>
## 実行ステップ（実測）
1. navigate → https://note.com/dashboard
2. snapshot → エディタ要素8個検出
3. click ref="new-article" → 記事作成画面に遷移
4. type ref="title" value="AIエージェントの現在地"
5. click ref="publish-btn" → 公開確認ダイアログ表示
## 短縮メモ
- ステップ2,3は1回のnavigate+snapshotで済む可能性あり
- 保存後の確認snapshotは省略可能か要検証
## 学び
- 発見した注意点やコツ
## エラー（該当時のみ）
- エラー内容と対処法
```

### I-4. サイトナレッジ更新

`knowledge/sites/<site名>/` の該当ファイルを Edit で更新する:

- 操作中に発見した注意点、有効なセレクタ、ページ遷移パターンを追記する
- 実行ルート（実際に辿ったページ遷移の順序）を記録する
- `index.md` の探索状況チェックリストを更新する

---

## Step J. レポーティング（フェーズ②③④のみ、E の直後）

再訪問時に、前回からの変化を比較・報告する。フェーズ①（初回）ではスキップ。
Step E（モニタリング）の直後、Step F（プランニング）の前に実行する。前回との差分を把握してから計画を立てるため。

### J-1. 差分抽出

1. 過去ログの `after_state`（前回操作後）と今回の `before_state`（Step E で記録済み）を比較する
2. 差異を以下のカテゴリに分類する:
   - **想定内の変化**: 前回の操作結果が維持されている
   - **外部変更**: 前回操作後に第三者が変更した項目
   - **リセット**: 前回の操作結果が元に戻っている

### J-2. 差分レポート生成

```
【前回からの変化レポート】
前回実行: <前回のタイムスタンプ>
今回確認: <今回のタイムスタンプ>

■ 変化なし
- field1: <値>（前回操作の結果が維持）

■ 外部変更あり
- field2: <前回の値> → <現在の値>（第三者による変更の可能性）

■ リセット検出
- field3: <前回操作後の値> → <現在の値>（前回の変更が戻っている）
```

### J-3. 影響判断

1. 外部変更・リセットがタスクの実行に影響する場合、ユーザーに報告して指示を仰ぐ
2. 影響がない場合、レポートを記録して Step K へ進む

---

## Step K. オファー

ユーザーに成果を報告する。

### K-1. 完了報告

以下を報告する:
- 実行結果（成功/失敗）
- 変更内容のサマリー（Before → After）
- 実行フェーズ（①〜④のどれだったか）
- 前回からの変化レポート（②③④の場合）
- 注意事項やエラーがあれば詳細
- 次回の最適化候補（短縮メモに基づく提案）

### K-2. チェックリスト最終出力

実行チェックリストの最終状態を出力する。全ステップが `[x]` になっていることを確認する。

---

## エラー処理

- ステップ実行中にエラーが発生した場合、タスクYAMLの `on_error` に従う
- デフォルト: `mcp__playwright__browser_take_screenshot` でスクリーンショットを撮り、状況をユーザーに報告して指示を仰ぐ
- ナレッジログにエラー内容を記録する
- **自動リカバリーは行わない**（AGENT.md の原則に従う）
