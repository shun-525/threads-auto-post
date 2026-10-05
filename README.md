# Threads 自動投稿（@shun_personal）

承認した投稿を、毎日 7:00・12:00・20:00（日本時間）に Threads へ自動投稿します。
20時の投稿には、公式LINEのURLを自分の返信として自動で付けます。

## 仕組み

```
posts.json（投稿の一覧）
   ↓  status を "approved"（承認）にしたものだけが対象
GitHub Actions が 7時・12時・20時台に15分おきに確認
   ↓  予定時刻を過ぎた承認済みの投稿を 1回に1件だけ投稿
Threads に投稿 → 返信（reply があれば）を付ける
   ↓
posts.json の status が "posted" に変わる
```

## ファイル

| ファイル | 内容 |
|---|---|
| `posts.json` | 投稿の一覧（本文・画像・予定時刻・状態） |
| `images/` | 投稿に使う画像（`001.png` のように番号で保存） |
| `scripts/threads_post.py` | 投稿プログラム |
| `.github/workflows/post.yml` | 自動投稿のスケジュール |
| `.github/workflows/refresh-token.yml` | トークンの自動延長（毎月1日・15日） |
| `.github/workflows/check-token.yml` | 接続テスト（手動で実行） |
| `画像プロンプト_テンプレート.md` | ナノバナナ用の画像プロンプト |

## posts.json の書き方

```json
{
  "id": "003",
  "scheduled_at": "2026-10-06T20:00:00+09:00",
  "status": "draft",
  "theme": "開いた肋骨 × ウエスト",
  "image": "images/003.png",
  "text": "本文（500文字まで）",
  "reply": "20時の投稿だけ：LINEのURLを入れた返信文"
}
```

### status（状態）の意味

| status | 意味 |
|---|---|
| `draft` | 下書き。投稿されません |
| `approved` | 承認済み。予定時刻になったら投稿されます |
| `posted` | 投稿済み |
| `failed` | 投稿できない状態（画像がない・文字数オーバーなど）。`error` に理由が書かれます。通信エラーなど一時的な失敗は `approved` のまま15分後に再挑戦します |
| `late` | 予定時刻から3時間以上遅れたため見送り（連投防止）。予定時刻を変えて `approved` に戻せば再投稿されます |

## 毎週の流れ

1. Claude に「来週分の21件を作って」と頼む
2. 本文と画像プロンプトを確認する（内容の正確さは鈴木さんがチェック）
3. ナノバナナで画像を作り、`images/` に番号どおり保存する
4. Claude に「承認」と伝える → `approved` にして GitHub に反映

## 初回の設定（1回だけ）

1. GitHub の Secrets に `THREADS_ACCESS_TOKEN`（Threads のアクセストークン）を登録
2. Actions の「Threads 接続テスト」を手動実行し、`@shun_personal` と表示されれば成功
3. （任意）トークン自動延長のため、Secrets の編集権限を持つ個人用トークンを `GH_PAT` として登録
   - 未設定の場合は、60日ごとに Meta の画面でトークンを作り直し、Secrets を更新してください

## 注意

- トークンは絶対に `posts.json` やこのリポジトリのファイルに書かないこと（Secrets にだけ保存）
- GitHub の混雑で、投稿が数分〜十数分遅れることがあります
