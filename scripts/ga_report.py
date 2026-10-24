#!/usr/bin/env python3
"""Google Analytics 4 report for pickshelf.github.io, pulled through the GA4 Data API.

Same approach as trablind's scripts/ga_report.py and staycat's ga_analyze.py: a service
account reads the property, so numbers can be pulled and analysed in chat without
opening the Analytics UI.

Shows: totals (visitors, sessions, page views), daily trend, top pages, where visitors
came from (channel and source/medium, including the utm_source inapp.js adds when it
moves a page out of Instagram/Threads/KakaoTalk), partner link clicks (analytics.js
link_click) by partner and item, and search-box terms.

Auth: pickshelf's own service account (Google Cloud project pickshelf-ga). Like the sister
repos, the variables carry the site prefix — several repos share one Claude Code
environment, and a key from another site must never be picked up by accident.
Checked in this order (first one set is used, a broken value fails):
    PICKSHELF_GA_SA_B64   base64-encoded service-account JSON
    PICKSHELF_GA_SA_JSON  raw service-account JSON
    --key PATH            JSON key file (local/testing)
The key must belong to SERVICE_ACCOUNT, and that address must be added to the pickshelf
GA4 property: GA4 → Admin → Property access management → + → Add users.
Viewer is enough for reports; Editor is needed once for --setup.

Behind the cloud egress proxy httplib2 breaks, so calls go through AuthorizedSession
(requests), as in the sister repos.

Usage:
    pip install google-auth requests
    python3 scripts/ga_report.py                # last 28 days
    python3 scripts/ga_report.py --days 7
    python3 scripts/ga_report.py --start 2026-10-01 --end 2026-10-23
    python3 scripts/ga_report.py --json         # raw JSON instead of tables
    python3 scripts/ga_report.py --include-bots # count headless-browser visits too
    python3 scripts/ga_report.py --setup        # register the link_click custom dimensions (Editor)
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import json
import os
import sys

# Numeric property ID (GA4 → Admin → Property details), not the G- measurement ID.
# Empty: looked up by PROPERTY_NAME among the properties the service account can see.
PROPERTY_ID = ""
PROPERTY_NAME = "pickshelf"
SERVICE_ACCOUNT = "pickshelf-ga-reader@pickshelf-ga.iam.gserviceaccount.com"
CREDENTIAL_SOURCES = (("PICKSHELF_GA_SA_B64", "base64"), ("PICKSHELF_GA_SA_JSON", "json"))
READ_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
EDIT_SCOPE = "https://www.googleapis.com/auth/analytics.edit"
DATA_API = "https://analyticsdata.googleapis.com/v1beta"
ADMIN_API = "https://analyticsadmin.googleapis.com/v1beta"

# Event parameters analytics.js sends with link_click. GA4 reports on them only after
# they are registered as event-scoped custom dimensions (--setup).
CUSTOM_DIMENSIONS = [
    ("partner", "파트너", "link_click: coupang / agoda / trip ..."),
    ("item_no", "상품 번호", "link_click: card number shown in the video"),
    ("item_name", "상품명", "link_click: card name"),
    ("link_type", "링크 종류", "link_click: partner / outbound / internal"),
    ("button", "버튼", "link_click: link class (card, ag, tr, main ...)"),
]

# Headless browsers that run the GA tag from data centres: square screen, no referrer.
# Seen on trablind.com and staycat.kr (see their ga_report/ga_analyze); applied here too.
BOT_RESOLUTIONS = ["1366x1366", "1280x1200", "1600x1600"]
BOT_SOURCES = ["(direct)", "(not set)"]
INCLUDE_BOTS = False


class GAError(Exception):
    """A fatal, user-facing error."""


def load_credentials(key_path: str | None, scopes: list[str]):
    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        raise GAError("Missing dependency. Run: pip install google-auth requests") from exc
    if key_path:
        with open(key_path, encoding="utf-8") as f:
            info, source = json.load(f), key_path
    else:
        for name, fmt in CREDENTIAL_SOURCES:
            value = os.environ.get(name, "").strip()
            if not value:
                continue
            try:
                if fmt == "base64":
                    value = base64.b64decode(value + "=" * (-len(value) % 4)).decode()
                info, source = json.loads(value), name
            except (binascii.Error, ValueError) as exc:
                raise GAError(f"{name} is not valid {fmt} service-account JSON.") from exc
            break
        else:
            raise GAError("Set PICKSHELF_GA_SA_B64 or PICKSHELF_GA_SA_JSON, or pass --key.")
    if info.get("client_email") != SERVICE_ACCOUNT:
        raise GAError(f"{source} is the key for {info.get('client_email')!r}, "
                      f"expected {SERVICE_ACCOUNT}.")
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


def make_session(creds):
    from google.auth.transport.requests import AuthorizedSession
    return AuthorizedSession(creds)


def find_property(session) -> str:
    if PROPERTY_ID:
        return PROPERTY_ID
    r = session.get(f"{ADMIN_API}/accountSummaries")
    if r.status_code != 200:
        raise GAError(f"accountSummaries failed: HTTP {r.status_code} {r.text[:300]}")
    seen = []
    for acc in r.json().get("accountSummaries", []):
        for p in acc.get("propertySummaries", []):
            seen.append(f"{p['displayName']} ({p['property'].split('/')[1]})")
            if PROPERTY_NAME in p["displayName"].lower():
                return p["property"].split("/")[1]
    raise GAError(f"No GA4 property named '{PROPERTY_NAME}' is shared with {SERVICE_ACCOUNT}. "
                  f"Add it under GA4 → Admin → Property access management. "
                  f"It can see: {', '.join(seen) or 'nothing'}.")


def bot_filter() -> dict:
    return {"andGroup": {"expressions": [
        {"filter": {"fieldName": "screenResolution", "inListFilter": {"values": BOT_RESOLUTIONS}}},
        {"filter": {"fieldName": "sessionSource", "inListFilter": {"values": BOT_SOURCES}}},
    ]}}


def run_report(session, prop, start, end, dimensions, metrics, limit=100,
               event=None, only_bots=False) -> dict:
    """event limits rows to one event name (e.g. link_click). Bots excluded unless INCLUDE_BOTS."""
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
        "orderBys": [{"metric": {"metricName": metrics[0]}, "desc": True}],
    }
    filters = []
    if only_bots:
        filters.append(bot_filter())
    elif not INCLUDE_BOTS:
        filters.append({"notExpression": bot_filter()})
    if event:
        filters.append({"filter": {"fieldName": "eventName", "stringFilter": {"value": event}}})
    if filters:
        body["dimensionFilter"] = filters[0] if len(filters) == 1 else {"andGroup": {"expressions": filters}}
    r = session.post(f"{DATA_API}/properties/{prop}:runReport", json=body)
    if r.status_code != 200:
        raise GAError(f"runReport({dimensions}/{metrics}) failed: HTTP {r.status_code} {r.text[:400]}")
    return r.json()


def rows(data: dict) -> list[dict]:
    dims = [h["name"] for h in data.get("dimensionHeaders", [])]
    mets = [h["name"] for h in data.get("metricHeaders", [])]
    out = []
    for row in data.get("rows", []):
        d = {dims[i]: v["value"] for i, v in enumerate(row["dimensionValues"])}
        d.update({mets[i]: v["value"] for i, v in enumerate(row["metricValues"])})
        out.append(d)
    return out


def n(v) -> int:
    return int(float(v))


def custom_dims_ready(session, prop) -> set[str]:
    r = session.get(f"{DATA_API}/properties/{prop}/metadata")
    if r.status_code != 200:
        return set()
    return {d["apiName"].split(":", 1)[1] for d in r.json().get("dimensions", [])
            if d["apiName"].startswith("customEvent:")}


def collect(session, prop, start, end, limit) -> dict:
    q = lambda *a, **k: run_report(session, prop, start, end, *a, **k)
    out = {
        "totals": q([], ["totalUsers", "newUsers", "sessions", "screenPageViews",
                         "averageSessionDuration"], limit=1),
        "daily": q(["date"], ["totalUsers", "sessions", "screenPageViews"], limit=400),
        "pages": q(["pagePath"], ["screenPageViews", "totalUsers"], limit=limit),
        "channels": q(["sessionDefaultChannelGroup"], ["sessions", "totalUsers"], limit=20),
        "sources": q(["sessionSource", "sessionMedium"], ["sessions", "totalUsers"], limit=limit),
        "clicks_by_page": q(["pagePath"], ["eventCount", "totalUsers"], limit=limit, event="link_click"),
        "searches": q(["searchTerm"], ["eventCount"], limit=limit, event="search"),
        "devices": q(["deviceCategory"], ["totalUsers"], limit=10),
    }
    if not INCLUDE_BOTS:
        out["bots"] = q([], ["sessions"], limit=1, only_bots=True)
    ready = custom_dims_ready(session, prop)
    if {"partner", "item_no", "item_name"} <= ready:
        out["clicks_by_partner"] = q(["customEvent:partner"], ["eventCount", "totalUsers"],
                                     limit=20, event="link_click")
        out["clicks_by_item"] = q(["pagePath", "customEvent:item_no", "customEvent:item_name"],
                                  ["eventCount"], limit=limit, event="link_click")
    return out


def print_report(data: dict, prop: str, start: str, end: str) -> None:
    print(f"pickshelf.github.io  GA4 property {prop}  {start} ~ {end}\n")
    t = (data["totals"].get("rows") or [{}])[0].get("metricValues")
    print("=== 요약 ===")
    if t:
        dur = n(t[4]["value"])
        print(f"  방문자 {n(t[0]['value'])}명 (신규 {n(t[1]['value'])})  세션 {n(t[2]['value'])}  "
              f"페이지뷰 {n(t[3]['value'])}  평균 체류 {dur // 60}분 {dur % 60:02d}초")
    else:
        print("  (이 기간 데이터 없음)")
    if "bots" in data:
        b = (data["bots"].get("rows") or [{}])[0].get("metricValues")
        print(f"  (봇 세션 {n(b[0]['value']) if b else 0}개 제외 — --include-bots 로 포함)")

    def table(title, key, fmt, empty="(없음)"):
        print(f"\n=== {title} ===")
        rs = rows(data[key]) if key in data else []
        for r in rs:
            print("  " + fmt(r))
        if not rs:
            print(f"  {empty}")

    data["daily"]["rows"] = sorted(data["daily"].get("rows", []), key=lambda r: r["dimensionValues"][0]["value"])
    table("일별 추이", "daily", lambda r: f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:]}  "
          f"방문자 {n(r['totalUsers']):>4}  세션 {n(r['sessions']):>4}  pv {n(r['screenPageViews']):>5}")
    table("페이지", "pages", lambda r: f"pv {n(r['screenPageViews']):>5}  방문자 {n(r['totalUsers']):>4}  {r['pagePath']}")
    table("유입 채널", "channels", lambda r: f"세션 {n(r['sessions']):>5}  방문자 {n(r['totalUsers']):>4}  "
          f"{r['sessionDefaultChannelGroup']}")
    table("유입 경로 (source / medium)", "sources", lambda r: f"세션 {n(r['sessions']):>5}  "
          f"방문자 {n(r['totalUsers']):>4}  {r['sessionSource']} / {r['sessionMedium']}")
    table("링크 클릭 (페이지별)", "clicks_by_page", lambda r: f"클릭 {n(r['eventCount']):>5}  "
          f"클릭한 사람 {n(r['totalUsers']):>4}  {r['pagePath']}")
    if "clicks_by_partner" in data:
        table("링크 클릭 (파트너별)", "clicks_by_partner", lambda r: f"클릭 {n(r['eventCount']):>5}  "
              f"클릭한 사람 {n(r['totalUsers']):>4}  {r['customEvent:partner'] or '(내부 링크)'}")
        table("링크 클릭 (상품별)", "clicks_by_item", lambda r: f"클릭 {n(r['eventCount']):>5}  "
              f"{r['pagePath']}  #{r['customEvent:item_no']}  {r['customEvent:item_name']}")
    else:
        print("\n  파트너·상품별 클릭은 맞춤 측정기준 등록 후 보여요: python3 scripts/ga_report.py --setup")
    table("검색어", "searches", lambda r: f"{n(r['eventCount']):>4}회  {r['searchTerm']}")
    table("기기", "devices", lambda r: f"방문자 {n(r['totalUsers']):>4}  {r['deviceCategory']}")


def setup_dimensions(session, prop) -> None:
    url = f"{ADMIN_API}/properties/{prop}/customDimensions"
    r = session.get(url)
    if r.status_code != 200:
        raise GAError(f"list customDimensions failed: HTTP {r.status_code} {r.text[:300]}")
    have = {d["parameterName"] for d in r.json().get("customDimensions", [])}
    for param, name, desc in CUSTOM_DIMENSIONS:
        if param in have:
            print(f"  있음    {param}")
            continue
        r = session.post(url, json={"parameterName": param, "displayName": name,
                                    "description": desc, "scope": "EVENT"})
        if r.status_code != 200:
            raise GAError(f"create {param} failed: HTTP {r.status_code} {r.text[:300]} "
                          f"(needs Editor on the property)")
        print(f"  등록함  {param} ({name})")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="GA4 report for pickshelf.github.io")
    p.add_argument("--days", type=int, default=28, help="look back N days (default 28)")
    p.add_argument("--start", help="start date YYYY-MM-DD (overrides --days)")
    p.add_argument("--end", help="end date YYYY-MM-DD (default today)")
    p.add_argument("--rows", type=int, default=15, help="rows per table (default 15)")
    p.add_argument("--key", help="service-account JSON key file instead of env")
    p.add_argument("--json", action="store_true", help="raw JSON instead of tables")
    p.add_argument("--include-bots", action="store_true", help="count headless-browser sessions too")
    p.add_argument("--setup", action="store_true", help="register link_click custom dimensions")
    args = p.parse_args(argv)

    global INCLUDE_BOTS
    INCLUDE_BOTS = args.include_bots
    end = args.end or dt.date.today().isoformat()
    start = args.start or (dt.date.fromisoformat(end) - dt.timedelta(days=args.days)).isoformat()
    try:
        scopes = [EDIT_SCOPE] if args.setup else [READ_SCOPE]
        session = make_session(load_credentials(args.key, scopes))
        prop = find_property(session)
        if args.setup:
            setup_dimensions(session, prop)
            return 0
        data = collect(session, prop, start, end, args.rows)
        if args.json:
            print(json.dumps({"property_id": prop, "start": start, "end": end, **data},
                             indent=2, ensure_ascii=False))
        else:
            print_report(data, prop, start, end)
    except GAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
