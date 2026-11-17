"""前日分（日本時間）の投稿結果をまとめて、GitHub の Issue として報告する。
Issue を作るとリポジトリの持ち主にメールが届く。"""
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
LABEL = {"posted": "✅ 投稿済み", "late": "⚠️ 見送り（4時間以上遅れ）",
         "failed": "❌ 失敗", "approved": "⏳ 未投稿", "draft": "📝 下書きのまま"}
WEEK = "月火水木金土日"

day = (datetime.now(JST) - timedelta(days=1)).date()
if len(sys.argv) > 1:
    day = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()

posts = [p for p in json.load(open("posts.json"))
         if datetime.fromisoformat(p["scheduled_at"]).astimezone(JST).date() == day]
posts.sort(key=lambda p: p["scheduled_at"])

ok = sum(p["status"] == "posted" for p in posts)
title_day = f"{day.month}/{day.day}（{WEEK[day.weekday()]}）"
mark = "✅ 全部完了" if posts and ok == len(posts) else f"⚠️ {len(posts) - ok}件 未完了"
title = f"投稿レポート {title_day}：{ok}/{len(posts)}件 {mark}"

lines = [f"@{os.environ.get('OWNER', '')}", "", f"## {title_day} の投稿結果", "",
         "| 予定 | 投稿 | 結果 | テーマ |", "|---|---|---|---|"]
for p in posts:
    s = datetime.fromisoformat(p["scheduled_at"]).astimezone(JST)
    a = p.get("posted_at")
    a = datetime.fromisoformat(a).astimezone(JST).strftime("%H:%M") if a else "—"
    lines.append(f"| {s:%H:%M} | {a} | {LABEL.get(p['status'], p['status'])} | {p.get('theme', p['id'])} |")
if not posts:
    lines.append("| — | — | 予定なし | — |")
if ok < len(posts):
    lines += ["", "見送り・失敗した投稿は、Claude に「レポートの見送り分を入れ直して」と伝えれば別の枠に入れ直します。"]
body = "\n".join(lines)
print(title); print(body)

if os.environ.get("GITHUB_ACTIONS"):
    subprocess.run(["gh", "issue", "create", "--title", title, "--body", body], check=True)
