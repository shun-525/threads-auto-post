"""投稿済みの投稿の反応（閲覧数・いいね・返信・リポスト）を一覧で表示する。

環境変数 THREADS_ACCESS_TOKEN が必要（GitHub Actions の「Threads 反応レポート」から実行）。
"""

import json
import os
from pathlib import Path

from threads_post import api

ROOT = Path(__file__).resolve().parent.parent
METRICS = ["views", "likes", "replies", "reposts", "quotes"]


def main():
    token = os.environ["THREADS_ACCESS_TOKEN"]
    posts = json.loads((ROOT / "posts.json").read_text(encoding="utf-8"))
    print("| id | 投稿日時 | テーマ | 閲覧 | いいね | 返信 | リポスト | 引用 |")
    print("|---|---|---|---|---|---|---|---|")
    for p in posts:
        if p["status"] != "posted" or not p.get("threads_id"):
            continue
        res = api("GET", f"{p['threads_id']}/insights", {"metric": ",".join(METRICS), "access_token": token})
        values = {m["name"]: m["values"][0]["value"] for m in res.get("data", [])}
        cells = " | ".join(str(values.get(m, "-")) for m in METRICS)
        print(f"| {p['id']} | {p['posted_at'][5:16]} | {p.get('theme', '')} | {cells} |")


if __name__ == "__main__":
    main()
