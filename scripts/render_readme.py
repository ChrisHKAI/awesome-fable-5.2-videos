#!/usr/bin/env python3
"""Render README.md from data/videos.json.

Edit the JSON, then run this, then scripts/validate.py.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "videos.json"
README = ROOT / "README.md"

CATEGORY_ANCHOR = {
    "code": "cat-code",
    "game": "cat-game",
    "av": "cat-av",
    "comparison": "cat-comparison",
}
CATEGORY_ORDER = ("code", "game", "av", "comparison")
SECTION_ORDER = (
    "official",
    "pricing",
    "benchmarks",
    "benchmark-roundup",
    "comparison",
)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def prompt_cell(item: dict) -> str:
    if not item["prompt_file"]:
        return "提示詞未公開"
    label = "提示詞"
    link = f'<a href="{esc(item["prompt_file"])}">{label}</a>'
    if item["prompt_partial"]:
        return link + "（部分）"
    return link


def tech_line(item: dict) -> str:
    parts = list(item["tech"])
    parts.append("作者自述")
    if item["comparison_with"]:
        parts.append("對照 " + "／".join(item["comparison_with"]))
    return " · ".join(parts)


def card(item: dict) -> str:
    post = esc(item["post_url"])
    preview = esc(item["preview_url"])
    title = esc(item["title"])
    author = esc(item["author"])
    author_url = esc(item["author_url"])
    subs = [f"<sub>{esc(tech_line(item))}</sub>"]
    subs.extend(f"<sub>{esc(line)}</sub>" for line in item["caveats"])
    sub_html = "<br>".join(subs)
    return (
        f'<td width="33%" valign="top">'
        f'<a href="{post}"><img src="{preview}" alt="{title}" width="100%"></a><br>'
        f'<a href="{post}"><b>{title}</b></a><br>'
        f'<a href="{author_url}">@{author}</a> · {prompt_cell(item)}<br>'
        f"{sub_html}</td>"
    )


def gallery_table(items: list[dict]) -> str:
    rows = []
    for index in range(0, len(items), 3):
        cells = "".join(card(item) for item in items[index : index + 3])
        rows.append(f"<tr>{cells}</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def clock(created_at: str) -> str:
    return created_at.replace(" Asia/Hong_Kong(UTC+8)", "")


def context_table(items: list[dict]) -> str:
    lines = [
        "| 時間 | 作者 | 原帖 | 說明 |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        summary = item["summary"].replace("|", "／").replace("\n", " ")
        if item["mythos_comparison"]:
            summary = "Mythos 5.2 對照。" + summary
        lines.append(
            "| {time} | [@{author}]({author_url}) | [帖]({post_url}) | {summary} |".format(
                time=clock(item["created_at"]),
                author=item["author"],
                author_url=item["author_url"],
                post_url=item["post_url"],
                summary=summary,
            )
        )
    return "\n".join(lines)


def excluded_block(excluded: list[dict], seed_count: int) -> str:
    rules = (
        "不進畫面畫廊的規則：只轉用官方宣傳片、把基準表做成影片、或轉述別人的作品。"
        "官宣片在官方區；[@0xCodinz](https://x.com/0xCodinz/status/2119869068740296916) 的基準影片在「基準整理片」。"
    )
    if not excluded:
        return (
            f"這一版沒有整則排除的帖。{seed_count} 則都在畫廊或上面的脈絡裡。\n\n"
            f"{rules}"
        )
    lines = [
        "下面這些帖有原帖連結，但**不計入畫面畫廊，也不算脈絡**。",
        "",
        "| 時間 | 作者 | 原帖 | 原因 |",
        "| --- | --- | --- | --- |",
    ]
    for item in excluded:
        reason = item["summary"].replace("|", "／").replace("\n", " ")
        lines.append(
            "| {time} | [@{author}]({author_url}) | [帖]({post_url}) | {reason} |".format(
                time=clock(item["created_at"]),
                author=item["author"],
                author_url=item["author_url"],
                post_url=item["post_url"],
                reason=reason,
            )
        )
    lines.append("")
    lines.append(
        "冰之大教堂（Cathedral of Ice）的同 prompt 原帖只收 @EnvolDev。"
        "@Shannnu_18、@karanC_12、@Phavorism、@wanerfu、@ZerouterAI 等搬運不另立條目，也不計入上面的數字。"
        "@renmu2017 另有一則火箭場景的價格帖，留在額度區，不是這支冰景的搬運。"
    )
    lines.append("")
    lines.append(rules)
    return "\n".join(lines)


def prompt_list(gallery: list[dict]) -> str:
    rows = []
    for item in gallery:
        if not item["prompt_file"]:
            continue
        kind = "部分" if item["prompt_partial"] else "全文"
        rows.append(
            f"- [{item['title']}]({item['prompt_file']}) · "
            f"[@{item['author']}]({item['post_url']}) · {kind}"
        )
    return "\n".join(rows)


def render(data: dict) -> str:
    meta = data["meta"]
    gallery = data["gallery"]
    context = data["context"]
    labels = meta["category_labels"]
    counts = meta["category_counts"]
    sections = meta["section_labels"]
    section_counts = meta["section_counts"]
    by_cat = {key: [item for item in gallery if item["category"] == key] for key in CATEGORY_ORDER}
    by_section = {
        key: [item for item in context if item["section"] == key] for key in SECTION_ORDER
    }
    sentinel = (
        f"seed={meta['seed_post_count']} gallery={meta['gallery_count']} "
        f"gallery_in_seed={meta['gallery_in_seed_count']} "
        f"gallery_resolved={meta['gallery_resolved_original_count']} "
        f"prompts={meta['prompt_file_count']} prompts_partial={meta['prompt_partial_count']} "
        f"context={meta['context_count']} excluded={meta['excluded_count']}"
    )
    toc = "\n".join(
        f"- [{labels[key]}](#{CATEGORY_ANCHOR[key]})（{counts[key]}）" for key in CATEGORY_ORDER
    )
    galleries = []
    for key in CATEGORY_ORDER:
        galleries.append(
            f'<a id="{CATEGORY_ANCHOR[key]}"></a>\n'
            f"## {labels[key]}（{counts[key]}）\n\n"
            f"{gallery_table(by_cat[key])}"
        )
    details = []
    for key in SECTION_ORDER:
        details.append(
            "<details>\n"
            f"<summary>{sections[key]}（{section_counts[key]}，不計入畫廊）</summary>\n\n"
            f"{context_table(by_section[key])}\n\n"
            "</details>"
        )
    prompt_files = prompt_list(gallery)
    body = f"""# Awesome Fable 5.2 Videos

**English.** {meta['gallery_count']} gallery entries, {meta['prompt_file_count']} public prompt, {meta['seed_post_count']} seed posts. Claude Fable 5.2 was announced on 2026-11-10 (HKT, UTC+8) together with Claude Mythos 5.2, by [@claudeai](https://x.com/claudeai/status/2119867114450268322) and [@AnthropicAI](https://x.com/AnthropicAI/status/2119867707546071125). Gallery entries are visual demos whose authors say they made them with Fable 5.2. The official launch video is under Official, not in the gallery. Benchmark roundups and retellings stay out of the gallery. Nothing here was independently reproduced. A prompt file exists only when the author published the exact wording; otherwise the prompt is null. Official API price is $8 / $40 per million tokens. Fast mode at $16 / $80 is second-hand and unverified.

<!-- {sentinel} -->

這份清單收集 **Claude Fable 5.2** 官宣前後的公開帖。畫面畫廊只放**作者自己說用 Fable 5.2 做出來的畫面**。官方宣傳片、把基準表做成的影片、轉述別人的結論，都不算進畫廊。

Anthropic 已在 2026-11-10（香港時間 HKT，UTC+8）宣布這個模型，並同時推出 Claude Mythos 5.2。本庫沒有重跑任何一條。預覽圖是原帖的公開縮圖，完整影片不下載、不轉存。縮圖失效時，以原帖為準。畫廊這 {meta['gallery_count']} 張預覽幀有看過；沒有把沒看到的成片內容寫成已經看過。

作者若把提示詞原文貼了出來，就按字收進 [`prompts/`](prompts/)。只描述了場景、或說「用了同一個 prompt」卻沒貼原文的，prompt 維持 null，畫廊寫「提示詞未公開」。

- 種子帖：{meta['seed_post_count']}（主清單蒐集於 {meta['seed_collected_at']}；同日稍後補入 {meta['late_post_count']} 則，互動與本輪補入的時間是 {meta['late_posts_collected_at']}）
- 畫廊：{meta['gallery_count']}（種子內原帖：{meta['gallery_in_seed_count']}；轉載還原：{meta['gallery_resolved_original_count']}）
- 公開提示詞：{meta['prompt_file_count']}（部分提示詞：{meta['prompt_partial_count']}；其餘畫廊條目的 prompt 為 null）
- 脈絡：{meta['context_count']}。已排除：{meta['excluded_count']}
- 資料快照：2026-11-10（香港時間 HKT，UTC+8）。互動數字不是即時

官方價格是每百萬 tokens 輸入 **$8**、輸出 **$40**（自 $10／$50），見 [@claudeai](https://x.com/claudeai/status/2119867138987176141) 與 [@ClaudeDevs](https://x.com/ClaudeDevs/status/2119868698613956992)。官方又說輸出最高約快 30%（相對 5.1）。Fast mode 的官方說法是輸出約 **2.5×**、價格 **2×**，見 [@ClaudeDevs](https://x.com/ClaudeDevs/status/2119868701994570178)，該帖沒有寫美元。社群常把 2× 寫成 **$16／$80**。這個美元數字是二手推算，**未核實**。

Mythos 5.2 的帖只在和 Fable 直接對照時留下，並在表裡標成 Mythos 5.2 對照。官方說兩者同底；Mythos 走網安／生命科學審核通道。

## 目錄

{toc}
- [提示詞怎麼用](#how-to-use)
- [脈絡，不計入畫廊](#context)
- [已排除](#excluded)
- [授權與出處](#credits)

{chr(10).join(galleries)}

<a id="how-to-use"></a>
## 提示詞怎麼用

公開原文只有這 {meta['prompt_file_count']} 份：

{prompt_files}

1. 打開提示詞檔，複製 **Prompt** 區塊。沒有檔的條目就是沒有公開全文，不要把標題、縮圖或本庫的說明當成提示詞。
2. 貼到你自己的 Claude 會話或程式代理。作者多半是在早期訪問或 Claude 產品裡跑的，你的額度、檔位和預設 Medium 不一定相同。
3. 原作若是 WebGL、Three.js 或瀏覽器遊戲，請它交付你能打開的檔，再用瀏覽器看。標成部分的提示詞不要預期相同畫面。直式剪輯那一份的其餘要求在作者的影片裡，不在本庫。
4. 做出類似的畫面，不能證明路線、檔位或價格和原帖一樣。本庫沒有重跑。
5. 官方建議多數日常任務先用 Opus 5.5，高難度再開 Fable。那是官方帖裡的話，不是本庫的測試結論。

<a id="context"></a>
## 脈絡，不計入畫廊

下面 {meta['context_count']} 則都在這 {meta['seed_post_count']} 篇種子裡，有原帖連結，但**不計入畫面畫廊**。官方宣傳片在「官方發布」。基準整理片、轉述和 YouTube 上的對比也在這裡。

{chr(10).join(details)}

<a id="excluded"></a>
## 已排除

{excluded_block(data["excluded"], meta["seed_post_count"])}

<a id="credits"></a>
## 授權與出處

畫面、提示詞和帖文歸原作者。MIT 只涵蓋這份清單自己的整理、結構和 [`scripts/validate.py`](scripts/validate.py)。完整說明在 [LICENSE](LICENSE)。

分區方式（畫廊、原帖連結、提示詞檔、使用步驟、脈絡與排除）沿用同作者的 [awesome-6.2-sol-videos](https://github.com/ChrisHKAI/awesome-6.2-sol-videos)，並參考 [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)（MIT）。本庫沒有重製網站，也不托管別人的影片。

要改一條或撤下自己的作品，請看 [CONTRIBUTING.md](CONTRIBUTING.md) 並開 issue。

核對方式：{meta['seed_post_count']} 篇種子帖都留了原帖連結。畫廊預覽幀有逐張看過的，在 `preview_frame_reviewed` 標成 true。沒有下載完整影片，也沒有把看不見的畫面寫成已經看過。互動數字是 {meta['snapshot_label']} 的快照。
"""
    return body


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    README.write_text(render(data), encoding="utf-8")
    print(f"wrote {README}")


if __name__ == "__main__":
    main()
