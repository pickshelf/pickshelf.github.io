#!/usr/bin/env python3
"""Write popular.json: how many people opened each card's partner link recently.

popular.js reads it and puts a "🔥 N명이 봤어요" mark on those cards, so visitors see what
others are looking at. Counts are people (totalUsers), not taps, so one visitor tapping
the same item five times counts once. Bots are excluded the same way as ga_report.py.

Items below MIN_USERS are left out: "1명이 봤어요" reads as "nobody wants this" and does
more harm than no mark at all. Until enough traffic builds up the file stays empty and
the pages show nothing.

Runs daily from .github/workflows/popular.yml (secret PICKSHELF_GA_SA_B64), or by hand:
    python3 scripts/popular.py              # write popular.json
    python3 scripts/popular.py --dry-run    # print it, including items under the threshold
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import ga_report as ga

DAYS = 30
MIN_USERS = 3
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "popular.json")


def page_key(path: str) -> str:
    path = path.split("?")[0].split("#")[0]
    if path.endswith("index.html"):
        path = path[: -len("index.html")]
    return path if path.endswith("/") else path + "/"


def collect(session, prop, start, end) -> dict[str, dict[str, int]]:
    data = ga.run_report(session, prop, start, end,
                         ["pagePath", "customEvent:item_no", "customEvent:link_type"],
                         ["totalUsers"], limit=2000, event="link_click")
    out: dict[str, dict[str, int]] = {}
    for r in ga.rows(data):
        no = r["customEvent:item_no"]
        if r["customEvent:link_type"] != "partner" or not no.isdigit():
            continue
        page = out.setdefault(page_key(r["pagePath"]), {})
        page[no] = page.get(no, 0) + ga.n(r["totalUsers"])
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="write popular.json for popular.js")
    p.add_argument("--days", type=int, default=DAYS, help=f"look back N days (default {DAYS})")
    p.add_argument("--min", type=int, default=MIN_USERS, help=f"leave out items under N people (default {MIN_USERS})")
    p.add_argument("--key", help="service-account JSON key file instead of env")
    p.add_argument("--dry-run", action="store_true", help="print all counts instead of writing the file")
    args = p.parse_args(argv)

    end = dt.date.today().isoformat()
    start = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    try:
        session = ga.make_session(ga.load_credentials(args.key, [ga.READ_SCOPE]))
        counts = collect(session, ga.find_property(session), start, end)
    except ga.GAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(counts, indent=1, ensure_ascii=False, sort_keys=True))
        return 0
    kept = {page: dict(sorted(((no, c) for no, c in items.items() if c >= args.min), key=lambda x: int(x[0])))
            for page, items in sorted(counts.items())}
    kept = {page: items for page, items in kept.items() if items}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"popular.json: {sum(map(len, kept.values()))} items with {args.min}+ people in {args.days} days")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
