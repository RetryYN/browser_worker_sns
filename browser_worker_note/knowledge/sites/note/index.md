# note.com サイトナレッジ

## 基本情報

- **URL**: https://note.com
- **エディタURL**: https://editor.note.com（記事編集時に自動リダイレクト）
- **アカウント**: akatu_unison（アイカツ！AI活用の現場から｜株式会社ユニゾンテクノロジー）
- **ログインURL**: https://note.com/login
- **認証方式**: メール+パスワード / Google / X / Apple（X・Google連携済み）

## ナビゲーション構造

### グローバルヘッダー（常時表示）

| 要素 | URL | 備考 |
|------|-----|------|
| noteロゴ | / | トップページ |
| 検索 | — | ボタンで展開 |
| メッセージ | /messages/rooms | |
| 通知 | — | ボタン（ドロップダウン） |
| メニュー | — | ボタン（ドロップダウン、下記参照） |
| 投稿 | /notes/new | editor.note.com にリダイレクト |
| 投稿メニュー | — | ボタン（種別選択） |

### メニュードロップダウン

| 項目 | URL |
|------|-----|
| クリエイターページ | /akatu_unison |
| ダッシュボード | /sitesettings/stats |
| 設定 | /settings/account |
| ポイント | /settings/point_history |
| 自分の記事 | /notes |
| 画像 | /creator_gallery |
| 購入した記事 | /notes/purchased |
| スキした記事 | /notes/liked |
| メンバーシップ | membership.lp-note.com |
| マガジン | /magazines/all |
| ログアウト | /logout（**操作禁止**） |

### ダッシュボード（/sitesettings/stats）

| サブタブ | URL |
|---------|-----|
| アクセス状況 | /sitesettings/stats |
| バッジ | /badges |
| 売上管理 | /sitesettings/salesmanage |
| 振込管理 | /sitesettings/transfer_history |
| 販売履歴 | /sitesettings/purchasers |

### 記事管理（/notes）

| サブタブ | URL |
|---------|-----|
| 自分の記事 | /notes |
| 高評価した | /notes/rated |
| 購入した | /notes/purchased |
| スキした | /notes/liked |
| 最近みた | /notes/viewed |

フィルター: 公開ステータス / 期間 / マガジン

### 設定（/settings/account）

| サブタブ | URL |
|---------|-----|
| アカウント | /settings/account |
| 通知 | /settings/notifications |
| メッセージ | /settings/messages |
| リアクション | /settings/reactions |
| 購入・チップ履歴 | /settings/purchase_history |
| ポイント管理 | /settings/point_history |
| カード情報 | /settings/credit_card |
| お支払先 | /settings/fee |
| 有料オプション | /settings/feature_subscriptions |

### フィード（トップページ）

| タブ | URL |
|-----|-----|
| すべて | / |
| フォロー中 | /following |
| 注目 | /recommend |
| 投稿企画 | /contests |

## 探索状況

- [x] トップページ（/）
- [x] メニュードロップダウン
- [x] ダッシュボード（/sitesettings/stats）
- [x] 記事一覧（/notes）
- [x] 記事エディタ（/notes/new → editor.note.com）→ 詳細: [article-editor.md](article-editor.md)
- [x] 公開設定画面（editor.note.com/notes/<id>/publish/）→ 詳細: [article-editor.md](article-editor.md#公開設定画面)
- [x] クリエイターページ（/akatu_unison）→ 詳細: [public-page.md](public-page.md)
- [x] 設定（/settings/account）→ 詳細: [settings.md](settings.md)
- [x] スキ設定（/like_reaction_setting）→ 詳細: [article-editor.md](article-editor.md#スキ設定画面投稿直後に遷移)
- [ ] マガジン（/magazines/all） — **優先度: 高**。トピック設計済みだが未作成。記事が5本以上溜まったら探索→作成
- [ ] 画像ギャラリー（/creator_gallery） — **優先度: 低**。運用上の必要性が出てから探索

## トピック設計（ハッシュタグ & マガジン）

記事にはトピックをタグとして付与する。noteのハッシュタグとマガジンに対応。

### トピック一覧

| トピック | ハッシュタグ | マガジン | 内容 |
|---------|------------|---------|------|
| ChatGPT | #ChatGPT | ChatGPT | ChatGPTの機能・使い方・アプデ |
| Claude | #Claude | Claude | Claudeの機能・使い方・アプデ |
| Gemini | #Gemini | Gemini | Geminiの機能・使い方・アプデ |
| Grok | #Grok | Grok | Grokの機能・使い方・アプデ |
| 画像生成 | #AI画像生成 | AI画像生成 | AI画像生成全般（DALL-E、Midjourney等） |
| プロンプト | #プロンプト | プロンプト | プロンプトの書き方・改善テクニック |
| AI比較 | #AI比較 | AI比較 | 複数AIの横並び検証 |
| AI活用術 | #AI活用 | AI活用術 | 業務での使い方・コツ |
| AIニュース | #AIニュース | AIニュース | 業界動向・アップデート速報 |
| AI裏側 | #AI裏側 | AI裏側 | このアカウントの制作過程 |

### サブトピック

メイントピックと組み合わせて使う。ハッシュタグとして付与するが、マガジンは作らない。

| サブトピック | ハッシュタグ | 用途 |
|------------|------------|------|
| Claude Code | #ClaudeCode | Claude Code の機能・活用 |
| Cursor | #Cursor | Cursor の機能・活用 |
| Codex | #Codex | OpenAI Codex CLI の機能・活用 |
| Sora | #Sora | Sora（動画生成AI）の機能・活用 |
| NotebookLM | #NotebookLM | Google NotebookLM の機能・活用 |
| DALL-E | #DALLE | DALL-E の画像生成 |
| Midjourney | #Midjourney | Midjourney の画像生成 |
| AI Idol Orchestra | #AIIdolOrchestra | このアカウントのキャラ・世界観 |

サブトピックは固定ではなく、新しいツール・サービスが出たら随時追加する。

### 運用ルール

- 1記事に**メイントピック1つ + サブトピック1-2個**を付与
- メイントピック = マガジンの振り分け先
- ハッシュタグはメイン + サブの両方を付ける
- AI比較の記事には比較対象のAI名タグも付ける（例: #AI比較 #ChatGPT #Claude）
- noteの共通ハッシュタグ（#AI #人工知能 等）も併用して検索流入を狙う

### ネタタイプとの対応

| ネタタイプ | 主なトピック |
|-----------|------------|
| update | 各AI名（ChatGPT/Claude/Gemini/Grok）、AIニュース |
| compare | AI比較 + 比較対象のAI名 |
| howto | プロンプト、AI活用術、画像生成 |
| trend | AIニュース |
| real | AI活用術、各AI名 |

### マガジン作成状況

- [ ] ChatGPT
- [ ] Claude
- [ ] Gemini
- [ ] Grok
- [ ] AI画像生成
- [ ] プロンプト
- [ ] AI比較
- [ ] AI活用術
- [ ] AIニュース
- [ ] AI裏側

→ マガジン作成は `/magazines/all` の探索後に実施

## 注意事項

- **ダッシュボードURL変更**: `/dashboard` は404。正しくは `/sitesettings/stats`
- **エディタは別ドメイン**: `editor.note.com` に自動リダイレクトされる
- **エディタ離脱時**: beforeunloadダイアログが表示される。`browser_handle_dialog(accept=true)` で処理
- **SPA遷移**: ページによっては初回ロードが遅い（3秒待機が必要な場合あり）
- **メール認証**: 投稿・購入・コメントにはメール認証完了が必要
- **投稿後の画面遷移**: 投稿する → スキ設定画面（/like_reaction_setting）→ noteトップ。スキ設定はスキップ可能
- **スキ画像**: 1枚のみ設定可。記事ごとの自動切替は不可。手動差し替えで対応
- **公開記事URL**: `https://note.com/akatu_unison/n/<記事ID>`
