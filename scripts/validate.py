#!/usr/bin/env python3
"""Check data/videos.json, prompts/, README.md, and x.com links.

Default mode is offline: schema, counts, prompt files, and the shape of
every x.com status link (well-formed and unique). ``--links`` rechecks URLs
and rewrites data/link-check.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "videos.json"
README = ROOT / "README.md"
LINKS = ROOT / "data" / "link-check.json"
PROMPTS = ROOT / "prompts"

REQUIRED_GALLERY = {
    "id",
    "slug",
    "author",
    "author_url",
    "post_url",
    "in_seed",
    "surfaced_via",
    "category",
    "title",
    "summary",
    "created_at",
    "attribution",
    "independently_reproduced",
    "comparison_with",
    "mythos_comparison",
    "tech",
    "prompt",
    "prompt_partial",
    "prompt_note",
    "prompt_file",
    "preview_url",
    "preview_frame_reviewed",
    "media",
    "caveats",
    "text",
    "metrics",
    "seed_category",
    "post_type",
}
CATEGORIES = {"code", "game", "av", "comparison"}
CATEGORY_LABELS = {
    "code": "代碼場景",
    "game": "遊戲與互動",
    "av": "影片、地圖與聲音",
    "comparison": "對照",
}
SECTIONS = {"official", "pricing", "benchmarks", "benchmark-roundup", "comparison"}
SECTION_LABELS = {
    "official": "官方發布",
    "pricing": "額度、速度與價格",
    "benchmarks": "編程與基準轉述",
    "benchmark-roundup": "基準整理片",
    "comparison": "同 prompt 對比，不進畫廊",
}
STATUS_URL = re.compile(r"^https://x\.com/([^/]+)/status/(\d+)$")
HKT = timezone(timedelta(hours=8))
TZ_SUFFIX = "Asia/Hong_Kong(UTC+8)"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def prompt_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*)\n```", text, re.S)
    if not match:
        raise ValueError(f"{path} has no ```text fence")
    return match.group(1)


def check_record_url(errors: list[str], item: dict, where: str) -> None:
    author = item["author"]
    post_id = item["id"]
    expected = f"https://x.com/{author}/status/{post_id}"
    post_url = item.get("post_url")
    match = STATUS_URL.match(post_url or "")
    if not match:
        fail(errors, f"{where} {post_id} post_url is not a well-formed x.com status link")
        return
    if match.group(1) != author or match.group(2) != post_id:
        fail(errors, f"{where} {post_id} post_url handle or id mismatch")
    if post_url != expected:
        fail(errors, f"{where} {post_id} post_url {post_url!r} != {expected}")
    if item.get("author_url") != f"https://x.com/{author}":
        fail(errors, f"{where} {post_id} author_url mismatch")
    created = item.get("created_at") or ""
    if not created.endswith(TZ_SUFFIX):
        fail(errors, f"{where} {post_id} timestamp is not {TZ_SUFFIX}")


def check(data: dict) -> list[str]:
    errors: list[str] = []
    meta = data["meta"]
    gallery = data["gallery"]
    context = data["context"]
    excluded = data["excluded"]

    if meta.get("official_release_confirmed") is not True:
        fail(errors, "official_release_confirmed must stay true")
    if meta.get("model_status") != "officially_announced":
        fail(errors, "model_status mismatch")
    if meta.get("model_name") != "Claude Fable 5.2":
        fail(errors, "model_name mismatch")
    if meta.get("independently_reproduced") is not False:
        fail(errors, "meta independently_reproduced must stay false")

    ids = [item["id"] for item in gallery + context + excluded]
    if len(ids) != len(set(ids)):
        dupes = [i for i, n in Counter(ids).items() if n > 1]
        fail(errors, f"duplicate ids: {dupes}")
    urls = [item["post_url"] for item in gallery + context + excluded]
    if len(urls) != len(set(urls)):
        fail(errors, "duplicate post urls")
    if any(not STATUS_URL.match(url) for url in urls):
        fail(errors, "a post url is not a well-formed x.com status link")
    slugs = [item["slug"] for item in gallery + context + excluded]
    if len(slugs) != len(set(slugs)):
        fail(errors, "duplicate slugs")

    in_seed = [item for item in gallery if item["in_seed"]]
    resolved = [item for item in gallery if not item["in_seed"]]
    # seed_post_count is the historical seed: in-seed gallery, excluded, and
    # the 53 context rows already catalogued at the 2026-11-12 17:55 HKT
    # snapshot. Context added after that stays in context_count only.
    seeded_context = meta["seed_post_count"] - len(in_seed) - len(excluded)
    if seeded_context != 53 or len(context) < seeded_context:
        fail(
            errors,
            f"seed coverage seeded_context={seeded_context} context={len(context)} "
            f"excluded={len(excluded)} != seed_post_count {meta['seed_post_count']}",
        )
    if len(gallery) != meta["gallery_count"]:
        fail(errors, "gallery_count mismatch")
    if len(in_seed) != meta["gallery_in_seed_count"]:
        fail(errors, "gallery_in_seed_count mismatch")
    if len(resolved) != meta["gallery_resolved_original_count"]:
        fail(errors, "gallery_resolved_original_count mismatch")
    if len(context) != meta["context_count"]:
        fail(errors, "context_count mismatch")
    if len(excluded) != meta["excluded_count"]:
        fail(errors, "excluded_count mismatch")
    # Pinned after the 2026-11-15 06:10 HKT sync
    # (105 at 2026-11-12 17:55 HKT; +7 gallery, +4 context -> 116 at
    # 2026-11-13 12:05 HKT; +27 gallery, +4 context).
    if len(ids) != 147:
        fail(errors, f"expected 147 posts, found {len(ids)}")

    by_cat = Counter(item["category"] for item in gallery)
    for key, label in CATEGORY_LABELS.items():
        if by_cat[key] != meta["category_counts"][key]:
            fail(errors, f"category {key} count mismatch")
        if meta["category_labels"][key] != label:
            fail(errors, f"category label {key} mismatch")

    by_section = Counter(item["section"] for item in context)
    for key, label in SECTION_LABELS.items():
        if by_section[key] != meta["section_counts"][key]:
            fail(errors, f"section {key} count mismatch")
        if meta["section_labels"][key] != label:
            fail(errors, f"section label {key} mismatch")

    prompt_items = [item for item in gallery if item["prompt"] is not None]
    partial = [item for item in prompt_items if item["prompt_partial"]]
    if len(prompt_items) != meta["prompt_file_count"]:
        fail(errors, "prompt_file_count mismatch")
    if len(partial) != meta["prompt_partial_count"]:
        fail(errors, "prompt_partial_count mismatch")

    raw = json.dumps(data, ensure_ascii=False)
    if "skillry" in raw.lower() or "video.twimg.com" in raw or ".mp4" in raw:
        fail(errors, "json contains a remake host or a full video file url")

    files_on_disk = sorted(p.name for p in PROMPTS.glob("*.md"))
    expected_files = sorted(Path(item["prompt_file"]).name for item in prompt_items)
    if files_on_disk != expected_files:
        fail(errors, f"prompt files {files_on_disk} != records {expected_files}")

    gallery_ids = {item["id"] for item in gallery}
    # Official launch video and the benchmark reel must not sit in the gallery.
    for banned in ("2119867114450268322", "2119869068740296916"):
        if banned in gallery_ids:
            fail(errors, f"{banned} must not be in the gallery")

    for item in gallery:
        missing = REQUIRED_GALLERY - item.keys()
        if missing:
            fail(errors, f"{item.get('id')} missing {sorted(missing)}")
            continue
        check_record_url(errors, item, "gallery")
        if item["category"] not in CATEGORIES:
            fail(errors, f"{item['id']} bad category")
        if item["seed_category"] not in {"畫面演示", "同 prompt 對比"}:
            fail(errors, f"{item['id']} gallery seed category {item['seed_category']}")
        if item["attribution"] != "creator_reported" or item["independently_reproduced"] is not False:
            fail(errors, f"{item['id']} attribution flags are wrong")
        if item["category"] == "comparison" and not item["comparison_with"]:
            fail(errors, f"{item['id']} comparison has no comparison_with")
        if item["mythos_comparison"]:
            fail(errors, f"{item['id']} mythos post is in the visual gallery")
        if not item["preview_url"].startswith("https://pbs.twimg.com/"):
            fail(errors, f"{item['id']} preview is not a public twimg url")
        if item["preview_frame_reviewed"] is not True:
            fail(errors, f"{item['id']} preview frame was not reviewed")
        # Gallery rows with in_seed false are outside the original seed.
        # They are counted by gallery_resolved_original_count.
        if item["prompt"] is None:
            if item["prompt_file"] is not None or item["prompt_partial"] is not False:
                fail(errors, f"{item['id']} null prompt still has a file or partial flag")
        else:
            if item["prompt_file"] != f"prompts/{item['slug']}.md":
                fail(errors, f"{item['id']} prompt_file path")
            body = prompt_body(PROMPTS / f"{item['slug']}.md")
            if body != item["prompt"]:
                fail(errors, f"{item['id']} prompt file does not match json")
            if item["prompt"] not in item["text"]:
                fail(errors, f"{item['id']} prompt is not an exact substring of the post")
            if "未公開" in item["prompt"]:
                fail(errors, f"{item['id']} prompt file contains a placeholder")

    for item in context:
        check_record_url(errors, item, "context")
        if item.get("counts_as_video") is not False:
            fail(errors, f"context {item['id']} counts_as_video")
        if item["section"] not in SECTIONS:
            fail(errors, f"context {item['id']} bad section")
        if item["id"] in MYTHOS_REQUIRED and not item["mythos_comparison"]:
            fail(errors, f"context {item['id']} mythos comparison is unlabeled")

    for item in excluded:
        check_record_url(errors, item, "excluded")
        if item.get("counts_as_video") is not False:
            fail(errors, f"excluded {item['id']} counts_as_video")

    readme = README.read_text(encoding="utf-8")
    if "skillry" in readme.lower():
        fail(errors, "README mentions the reference remake brand")
    sentinel = (
        f"seed={meta['seed_post_count']} gallery={meta['gallery_count']} "
        f"gallery_in_seed={meta['gallery_in_seed_count']} "
        f"gallery_resolved={meta['gallery_resolved_original_count']} "
        f"prompts={meta['prompt_file_count']} prompts_partial={meta['prompt_partial_count']} "
        f"context={meta['context_count']} excluded={meta['excluded_count']}"
    )
    if sentinel not in readme:
        fail(errors, "README count sentinel missing or stale")
    for phrase in (
        f"種子帖：{meta['seed_post_count']}",
        f"畫廊：{meta['gallery_count']}",
        f"種子內原帖：{meta['gallery_in_seed_count']}",
        f"轉載還原：{meta['gallery_resolved_original_count']}",
        f"公開提示詞：{meta['prompt_file_count']}",
        f"部分提示詞：{meta['prompt_partial_count']}",
        f"{meta['gallery_count']} gallery entries",
        f"{meta['seed_post_count']} seed posts",
        f"{meta['prompt_file_count']} public prompt",
        "2026-11-10",
        "HKT",
        "$8",
        "$40",
        "$16 / $80",
        "未核實",
        "Asia/Hong_Kong",
    ):
        if phrase not in readme:
            fail(errors, f"README missing phrase: {phrase}")
    for key, label in CATEGORY_LABELS.items():
        heading = f"## {label}（{meta['category_counts'][key]}）"
        if heading not in readme:
            fail(errors, f"README missing heading {heading}")
    for key, label in SECTION_LABELS.items():
        heading = f"{label}（{meta['section_counts'][key]}，不計入畫廊）"
        if heading not in readme:
            fail(errors, f"README missing section heading {heading}")
    for item in gallery + context + excluded:
        if item["post_url"] not in readme:
            fail(errors, f"README missing {item['post_url']}")
    readme_full = re.findall(r"https://x\.com/[^/\s)\"']+/status/\d+", readme)
    bad_readme = [url for url in readme_full if not STATUS_URL.match(url)]
    if bad_readme:
        fail(errors, f"README has malformed status urls: {bad_readme}")
    if set(readme_full) != set(urls):
        missing = sorted(set(urls) - set(readme_full))
        extra = sorted(set(readme_full) - set(urls))
        fail(errors, f"README status urls drift missing={missing} extra={extra}")
    if len(urls) != len(set(urls)):
        fail(errors, "status urls are not unique")

    if not LINKS.exists():
        fail(errors, "data/link-check.json missing; run python3 scripts/validate.py --links")
    else:
        link_data = json.loads(LINKS.read_text(encoding="utf-8"))
        by_url = {row["url"]: row for row in link_data["results"]}
        if len(link_data["results"]) != len(by_url):
            fail(errors, "link-check.json repeats a url")
        for item in gallery + context + excluded:
            row = by_url.get(item["post_url"])
            if not row:
                fail(errors, f"link check missing {item['post_url']}")
            elif row["class"] == "dead":
                fail(errors, f"status url dead: {item['post_url']}")
            elif not STATUS_URL.match(row["url"]):
                fail(errors, f"link check stored a bad status url: {row['url']}")
        for item in gallery:
            row = by_url.get(item["preview_url"])
            if not row:
                fail(errors, f"link check missing {item['preview_url']}")
            elif row["class"] == "dead":
                fail(errors, f"gallery preview dead: {item['preview_url']}")
            elif row["class"] not in {"ok", "blocked"}:
                fail(errors, f"gallery preview {row['class']}: {item['preview_url']}")
        summary = Counter(row["class"] for row in link_data["results"])
        if summary != Counter(link_data["summary"]):
            fail(errors, "link-check summary does not match rows")
    return errors


MYTHOS_REQUIRED = {"2119867126613954736", "2119867136361316437"}


def classify_http(status: int, body: str, url: str) -> str:
    if status in {404, 410}:
        return "dead"
    if status in {401, 403, 429}:
        return "blocked"
    if status == 200:
        if "x.com/" in url or "twitter.com/" in url:
            status_id = url.rstrip("/").split("/")[-1]
            if status_id and status_id not in body and url not in body:
                return "blocked"
        return "ok"
    if status >= 500 or status == 0:
        return "error"
    return "blocked"


def fetch(url: str, method: str = "GET") -> tuple[int, str]:
    req = Request(
        url,
        method=method,
        headers={"User-Agent": "awesome-fable-5.2-videos-validator"},
    )
    try:
        with urlopen(req, timeout=25) as response:
            raw = response.read(180_000)
            return response.status, raw.decode("utf-8", "replace")
    except HTTPError as exc:
        body = exc.read(80_000).decode("utf-8", "replace") if exc.fp else ""
        return exc.code, body
    except URLError as exc:
        return 0, str(exc)


def refresh_links(data: dict) -> None:
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(url: str, kind: str) -> None:
        if url and url not in seen:
            seen.add(url)
            urls.append((url, kind))

    for item in data["gallery"]:
        add(item["post_url"], "post")
        add(item["preview_url"], "preview")
    for item in data["context"] + data["excluded"]:
        add(item["post_url"], "post")
    for url in data["meta"].get("extra_checked_urls", []):
        add(url, "external")

    results = []
    for url, kind in urls:
        if not STATUS_URL.match(url) and kind == "post":
            raise SystemExit(f"refusing to check a malformed post url: {url}")
        method = "HEAD" if kind == "preview" else "GET"
        status, body = fetch(url, method)
        if kind == "preview" and status in {0, 405, 501}:
            status, body = fetch(url, "GET")
        if status == 0:
            status, body = fetch(url, method)
        results.append(
            {
                "url": url,
                "kind": kind,
                "http_status": status,
                "class": classify_http(status, body, url),
            }
        )
        print(f"{results[-1]['class']:7} {status:3} {kind:8} {url}", flush=True)
    summary = dict(Counter(row["class"] for row in results))
    for key in ("ok", "blocked", "dead", "error"):
        summary.setdefault(key, 0)
    payload = {
        "checked_at": datetime.now(HKT).strftime("%Y-%m-%d %H:%M:%S Asia/Hong_Kong(UTC+8)"),
        "method": "GET x.com status pages (HTML must contain the status id, else blocked); HEAD preview images on pbs.twimg.com; every status url is matched to https://x.com/{handle}/status/{id} and checked unique before the request",
        "summary": summary,
        "results": results,
    }
    LINKS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", LINKS, summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--links", action="store_true", help="recheck URLs and rewrite data/link-check.json")
    args = parser.parse_args()
    data = load()
    if args.links:
        refresh_links(data)
        data = load()
    errors = check(data)
    if errors:
        print(f"{len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    meta = data["meta"]
    print(
        f"ok gallery={meta['gallery_count']} prompts={meta['prompt_file_count']} "
        f"seed={meta['seed_post_count']} context={meta['context_count']} excluded={meta['excluded_count']}"
    )
    print("x.com status links: well-formed and unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
