"""content/<週>.py から、posts.json の下書きと画像プロンプト集を作る。

使い方:
  python3 scripts/build_week.py week1

- posts.json：同じ id の下書き（draft）は上書き。投稿済み・承認済みは変更しない
- 画像プロンプト_<週名>.md：Gemini にそのまま貼り付けられるプロンプトを1件ずつ
"""

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_FILE = ROOT / "posts.json"
WEEKDAYS = "月火水木金土日"

LINE_CTA = "\n\n🎁 姿勢改善の教科書を無料プレゼント中\n受け取りは返信欄から⤵︎"
LINE_REPLY = "🎁 姿勢改善の教科書の受け取りはこちら\nhttps://lin.ee/k9BwPKA"

RULES = """━━ 最も大事なルール（必ず守ってください）━━
1. 写真ではなく、医療パンフレットのような清潔感のある「解剖イラスト」で描いてください。
2. 画像内の日本語は、この指示文の「」で囲んだ文章を一字一句そのまま使ってください。言い換え・要約・追加の文章は入れないでください。
   理由：専門家が内容を確認した文章なので、変わると誤った情報になるためです。
3. 解剖学的に正確に描いてください。この指示に書かれていない筋肉・骨・臓器を強調したり、名前のラベルを付けたりしないでください。
   理由：読者は姿勢改善を学びたい一般の方で、間違った位置を覚えると誤ったケアにつながるためです。
4. 説明ラベルは、各パネルに指定した3つだけにしてください。引き出し線は、必ずラベルの内容と一致する部位を正確に指してください。
5. 手や前腕など、指示にない体の部位を付け足さないでください。
   理由：描くものが増えると、体の形が不自然になりやすいためです。"""

STYLE = """━━ スタイル ━━
・色は青・水色・クリーム・こげ茶が基調。赤＝問題、緑＝改善、黄色＝大事なところ。
・文字は大きめ。詰め込みすぎず、余白を適度にとる。
・同じラベルを2回使わない。指定以外の文字・線・記号は入れない。"""


def labels(items):
    return "\n".join(f"  「{t}」→ {target}を指す（理由：{why}）" for t, target, why in items)


def bullets(lines):
    return "\n".join(f"・{line}" for line in lines)


def prompt(img):
    return f"""日本語の医療解説インフォグラフィックを1枚作成してください。横長（16:9）。

{RULES}

━━ この画像で伝えたいこと ━━
{img["mechanism"]}

━━ 描く体の部位と位置関係 ━━
・視点：{img["view"]}
{bullets(img["parts"])}
・それ以外の筋肉は、薄いベージュで目立たせずに描く。

━━ レイアウト ━━

■ 1. 見出し帯（上部・横いっぱい）
・濃い青のグラデーションの帯に、白い極太ゴシック体で「{img["headline"]}」。
・「{img["em"]}」だけ黄色の文字。

■ 2. 左パネル（BEFORE）
・上部にこげ茶の帯、白文字で「{img["before_title"]}」。背景はクリーム色。
{bullets(img["before"])}
・説明ラベル（この3つだけ）：
{labels(img["before_labels"])}
・右下に、{img["before_figure"]}の小さな全身イラストと、吹き出し「{img["bubble"]}」。

■ 3. 中央の矢印
・左から右へ、2つのパネルにまたがる太い青色の矢印。中に白文字で「{img["center"]}」。

■ 4. 右パネル（AFTER）
・上部に水色の帯、白文字で「{img["after_title"]}」。背景は淡い水色。
{bullets(img["after"])}
・説明ラベル（この3つだけ）：
{labels(img["after_labels"])}
・右下に、きれいな姿勢の女性の小さな全身イラスト（グレーのタンクトップ、ピンクのレギンス）と緑のチェック。

■ 5. まとめ帯（下部・横いっぱい）
・淡い水色の帯に、濃い紺色の太字で「{img["summary"]}」。
・「{img["summary_em"]}」に黄色の蛍光マーカー。右下に小さな白い光の装飾。

{STYLE}"""


def when(at):
    dt = datetime.fromisoformat(at)
    return f"{dt.month}/{dt.day}（{WEEKDAYS[dt.weekday()]}）{dt:%H:%M}"


def main():
    week_key = sys.argv[1] if len(sys.argv) > 1 else "week1"
    spec = importlib.util.spec_from_file_location(week_key, ROOT / "content" / f"{week_key}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in posts}
    md = [
        f"# 画像プロンプト（{mod.WEEK}）",
        "",
        "各プロンプトの枠の中をすべてコピーして、Gemini（ナノバナナ）に貼り付けてください。",
        "できた画像は、Gemini のダウンロードボタンで保存し、`images` フォルダに **番号.jpg**（例：`002.jpg`）の名前で入れてください。",
        "",
    ]

    for item in mod.POSTS:
        text = item["text"] + (LINE_CTA if item.get("line") else "")
        if len(text) > 500:
            sys.exit(f"{item['id']} の本文が {len(text)} 文字です（上限500）")
        existing = by_id.get(item["id"])
        if existing and existing["status"] != "draft":
            print(f"{item['id']} は {existing['status']} のため変更しません")
        else:
            entry = {
                "id": item["id"],
                "scheduled_at": item["at"] + ":00+09:00",
                "status": "draft",
                "theme": item["theme"],
                "image": f"images/{item['id']}.jpg",
                "text": text,
            }
            if item.get("line"):
                entry["reply"] = LINE_REPLY
            if existing:
                posts[posts.index(existing)] = entry
            else:
                posts.append(entry)
            by_id[item["id"]] = entry

        md += [
            "---",
            "",
            f"## {item['id']}｜{when(item['at'])}｜{item['theme']}" + ("　🎁LINE誘導あり" if item.get("line") else ""),
            "",
            "**本文**",
            "",
            "```",
            text,
            "```",
            "",
        ]
        if item.get("line"):
            md += ["**自動で付ける返信**", "", "```", LINE_REPLY, "```", ""]
        md += ["**画像プロンプト**", "", "```", prompt(item["img"]), "```", ""]

    posts.sort(key=lambda p: p["scheduled_at"])
    POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = ROOT / f"画像プロンプト_{mod.WEEK}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"{len(mod.POSTS)} 件を posts.json に反映し、{out.name} を作成しました")


if __name__ == "__main__":
    main()
