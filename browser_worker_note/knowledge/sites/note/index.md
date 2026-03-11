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
- [ ] マガジン（/magazines/all）
- [ ] 画像ギャラリー（/creator_gallery）

## 注意事項

- **ダッシュボードURL変更**: `/dashboard` は404。正しくは `/sitesettings/stats`
- **エディタは別ドメイン**: `editor.note.com` に自動リダイレクトされる
- **エディタ離脱時**: beforeunloadダイアログが表示される。`browser_handle_dialog(accept=true)` で処理
- **SPA遷移**: ページによっては初回ロードが遅い（3秒待機が必要な場合あり）
- **メール認証**: 投稿・購入・コメントにはメール認証完了が必要
