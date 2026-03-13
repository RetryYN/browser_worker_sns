# ブラウザ操作パターン集

サイト横断で使えるワークアラウンドと定型パターン。
各サイト固有の手順はサイト別ナレッジ（`knowledge/sites/<site>/`）を参照。

## textarea への値セット（nativeInputValueSetter パターン）

**問題**: 一部サイト（X等）の `<textarea>` に `browser_type(slowly: true)` を使うとタイムアウトする。

**解決**: `browser_evaluate` で React の内部ステートを直接更新する。

```javascript
// textarea の場合
() => {
  const el = document.querySelector('textarea[name="description"]');
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, 'value'
  ).set;
  setter.call(el, 'NEW_TEXT_HERE');
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

// input[type="text"] の場合
() => {
  const el = document.querySelector('input[name="fieldName"]');
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  setter.call(el, 'NEW_TEXT_HERE');
  el.dispatchEvent(new Event('input', { bubbles: true }));
}
```

### 適用条件

- `browser_type(slowly: true)` でタイムアウトが発生した場合
- React/Next.js 等の SPA で value が制御されているフォーム
- セレクタは毎回 `browser_snapshot` で確認する（ハードコードしない）

### 実績

| サイト | 要素 | セレクタ例 | セッション |
|--------|------|-----------|-----------|
| X | 自己紹介 textarea | `textarea[name="description"]` | セッション12 |

---

## テキスト入力の上書き（select-all + type）

既存テキストを全選択してから新しいテキストを入力する。

```
1. browser_click → 対象フィールドをフォーカス
2. browser_press_key → "Control+a"（全選択）
3. browser_type → 新しいテキスト（slowly: true）
```

### 適用条件

- `<input type="text">` で既存テキストを置換する場合
- `slowly: true` でタイムアウトしない通常の input 要素

### 実績

| サイト | 要素 | セッション |
|--------|------|-----------|
| X | 名前 input | セッション12 |

---

## 画像アップロード（click + file_upload）

```
1. browser_click → 「画像を追加」ボタン
2. browser_file_upload → ファイルパス指定（ファイルチューザーは自動検出）
3. （クロップダイアログが出る場合）browser_click → 「適用」ボタン
```

### 注意点

- ファイルチューザーは `browser_click` 後に自動で検出される
- クロップダイアログが表示される場合がある（X のプロフィール画像等）
- デフォルトクロップで良ければ「適用」を押すだけ

---

## SPA のページ遷移待機

SPA（X, note 等）では `browser_navigate` 後にコンテンツが非同期でロードされる。

```
1. browser_navigate → URL
2. browser_wait_for → 5000ms（初回ロード）
   または browser_wait_for → 特定の要素セレクタ
3. browser_snapshot → 構造確認
```

### 目安待機時間

| サイト | 初回ロード | ページ内遷移 |
|--------|-----------|-------------|
| X | 5秒 | 2秒 |
| note | 3秒 | 2秒 |

---

## beforeunload ダイアログの処理

note のエディタ等、編集中に離脱すると「変更が失われます」ダイアログが表示される。

```
1. browser_handle_dialog → accept: true（事前に設定）
2. browser_navigate → 別ページへ遷移
```

### サイト別の beforeunload 挙動

| サイト | beforeunload |
|--------|-------------|
| note | あり（エディタ画面） |
| X | なし |

---

## 日本語入力の注意点

- `browser_type` に `slowly: true` を指定する（IME 変換の安定化）
- 長文（100文字超）の場合はタイムアウトリスクあり → nativeInputValueSetter パターンを検討
- `browser_fill_form` は日本語で不安定な場合がある → `browser_type` を優先
