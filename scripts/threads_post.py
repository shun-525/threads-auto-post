"""承認済みで投稿時刻を過ぎた投稿を、Threads に 1 件投稿する。

GitHub Actions から 15 分おきに呼ばれる想定。標準ライブラリだけで動く。

環境変数:
  THREADS_ACCESS_TOKEN  Threads の長期アクセストークン（必須）
  GITHUB_REPOSITORY     画像の公開URLを組み立てるのに使う（Actions が自動で設定）
  IMAGE_BRANCH          画像を置いているブランチ（省略時 main）

使い方:
  python3 scripts/threads_post.py            投稿する
  python3 scripts/threads_post.py --dry-run  何が投稿されるかだけ表示
  python3 scripts/threads_post.py --whoami   トークンが有効か確認
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.threads.net/v1.0"
ROOT = Path(__file__).resolve().parent.parent
POSTS_FILE = ROOT / "posts.json"
JST = timezone(timedelta(hours=9))
MAX_TEXT = 500
# これより古い未投稿は、まとめて連投しないよう「late」にして人の判断に回す
LATE_LIMIT = timedelta(hours=3)


def api(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        url += "?" + data.decode()
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Threads API エラー {e.code}: {body}") from None


def wait_until_ready(container_id, token):
    # 画像はThreads側の処理が終わるまで公開できない
    for _ in range(20):
        status = api("GET", container_id, {"fields": "status,error_message", "access_token": token})
        if status.get("status") == "FINISHED":
            return
        if status.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"メディア処理に失敗: {status}")
        time.sleep(5)
    raise RuntimeError("メディア処理がタイムアウトしました")


def publish(user_id, token, text, image_url=None, reply_to=None):
    params = {"text": text, "access_token": token}
    if image_url:
        params.update(media_type="IMAGE", image_url=image_url)
    else:
        params["media_type"] = "TEXT"
    if reply_to:
        params["reply_to_id"] = reply_to
    container = api("POST", f"{user_id}/threads", params)["id"]
    wait_until_ready(container, token)
    return api("POST", f"{user_id}/threads_publish", {"creation_id": container, "access_token": token})["id"]


def image_url_for(path):
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY が未設定のため画像URLを作れません")
    branch = os.environ.get("IMAGE_BRANCH", "main")
    quoted = urllib.parse.quote(path)
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{quoted}"


def validate(post):
    problems = []
    if len(post["text"]) > MAX_TEXT:
        problems.append(f"本文が{len(post['text'])}文字（上限{MAX_TEXT}）")
    if post.get("reply") and len(post["reply"]) > MAX_TEXT:
        problems.append("返信が500文字を超えています")
    if post.get("image") and not (ROOT / post["image"]).exists():
        problems.append(f"画像ファイルがありません: {post['image']}")
    return problems


def load():
    return json.loads(POSTS_FILE.read_text(encoding="utf-8"))


def save(posts):
    POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    args = set(sys.argv[1:])
    token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not token and "--dry-run" not in args:
        sys.exit("THREADS_ACCESS_TOKEN が設定されていません")

    if "--whoami" in args:
        me = api("GET", "me", {"fields": "id,username", "access_token": token})
        print(f"トークンは有効です: @{me['username']} (id {me['id']})")
        return

    now = datetime.now(JST)
    posts = load()
    due = sorted(
        (p for p in posts if p["status"] == "approved" and datetime.fromisoformat(p["scheduled_at"]) <= now),
        key=lambda p: p["scheduled_at"],
    )

    changed = False
    for p in due:
        if now - datetime.fromisoformat(p["scheduled_at"]) > LATE_LIMIT:
            p["status"] = "late"
            p["error"] = f"{now:%m/%d %H:%M} 時点で予定から3時間以上過ぎたため投稿を見送り"
            print(f"[{p['id']}] 予定時刻を大きく過ぎたため見送り")
            changed = True
    due = [p for p in due if p["status"] == "approved"]

    if not due:
        print("投稿する予定のものはありません")
        if changed:
            save(posts)
        return

    post = due[0]  # 1回の実行で投稿するのは1件だけ（連投防止）
    problems = validate(post)
    if "--dry-run" in args:
        print(f"[{post['id']}] {post['scheduled_at']} に投稿予定")
        print(post["text"])
        if post.get("image"):
            print(f"画像: {post['image']}")
        if post.get("reply"):
            print(f"--- 返信 ---\n{post['reply']}")
        for msg in problems:
            print(f"⚠️ {msg}")
        return

    if problems:
        post["status"] = "failed"
        post["error"] = " / ".join(problems)
        save(posts)
        sys.exit(f"[{post['id']}] 投稿できません: {post['error']}")

    try:
        user_id = api("GET", "me", {"fields": "id", "access_token": token})["id"]
        image_url = image_url_for(post["image"]) if post.get("image") else None
        post_id = publish(user_id, token, post["text"], image_url=image_url)
        post["status"] = "posted"
        post["posted_at"] = datetime.now(JST).isoformat(timespec="seconds")
        post["threads_id"] = post_id
        post.pop("error", None)
        print(f"[{post['id']}] 投稿しました (threads id {post_id})")

        if post.get("reply"):
            time.sleep(10)  # 本投稿が反映されてから返信する
            post["reply_id"] = publish(user_id, token, post["reply"], reply_to=post_id)
            print(f"[{post['id']}] 返信を付けました")
    except Exception as e:
        if post["status"] != "posted":
            post["status"] = "failed"
        post["error"] = str(e)
        save(posts)
        sys.exit(f"[{post['id']}] {e}")

    save(posts)


if __name__ == "__main__":
    main()
