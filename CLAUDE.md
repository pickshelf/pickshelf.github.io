# pickshelf.github.io

"골라둔 물건들": a static GitHub Pages site (no build step) that collects affiliate picks
shared from Threads/Instagram posts. Korean audience, mostly mobile.

| Path | What | Links |
|---|---|---|
| `/` | Hub page linking to the three lists | - |
| `/travel/` | Travel gear (여행 준비물) | Coupang |
| `/living/` | Everyday items (생활용품) | Coupang |
| `/hotels/` | ~400 hotels in 12 cities, filters for city/zone, style, price tier | Agoda, Trip.com |

Each `index.html` holds its own data, CSS and JS inline. Shared scripts at the root:
`inapp.js` (in-app browser handling) and `analytics.js` (GA4).

## Editing rules

- **Cards**: `<… class="card" id="N" data-no="N" data-k="search keywords">`. `N` is the number
  shown in the post/video, so never renumber existing cards. Add new ones at the end.
- **Affiliate links** carry `rel="sponsored noopener"`. Both scripts depend on it: inapp.js routes
  sponsored links into apps, and analytics.js records `link_type=partner`.
- **Deep links**: `/hotels/#116` puts `116` in the search box and shows only card 116. `#<category>`
  opens that city tab, and `#s-<style>` / `#t-<tier>` select a filter. Use these in posts instead of
  bare `/hotels/` or `/travel/`.
- **Cache busting**: pages load `/inapp.js?v=N` and `/analytics.js?v=N`. When you change either script,
  bump `v` in all four pages.
- After a push, GitHub Pages takes a minute or two to update. Check with `curl`, adding a throwaway
  query string to get past the cache.

## In-app browsers (inapp.js)

Threads, Instagram and KakaoTalk open links in their own webview, where shopping and booking apps
and saved logins don't work.

- **Android and KakaoTalk**: the page moves itself to the default browser once (`intent://`, or
  Kakao's openExternal) and adds `utm_source=<app>&utm_medium=social`. Sponsored links go through
  an intent naming the Agoda/Trip.com app. Coupang links are deliberately left alone (see the
  comment in inapp.js).
- **iOS**: apps don't let a page leave by itself, so it shows a banner with a `x-safari-` button
  instead. Verified in GA on 2026-10-24: every Android visit from Threads ended up in Chrome or
  Samsung Internet, while all ~21 iOS Threads sessions stayed in `Safari (in-app)` with almost no
  engagement or clicks. If iOS traffic matters, the banner is the only lever.
- analytics.js waits 3 s before counting an in-app page view that is about to move out, so the
  visit isn't counted twice.

## Google Analytics 4

| | |
|---|---|
| Measurement ID | `G-VDRYK1K890` (set in `analytics.js`) |
| Property | `pickshelf`, ID `560488821`, under the 트래블라인드 account |
| Service account | `pickshelf-ga-reader@pickshelf-ga.iam.gserviceaccount.com`, Editor on the property only |
| GCP project | `pickshelf-ga`, **billing disabled** (the GA Data/Admin APIs are free and work without it) |
| Credentials | env `PICKSHELF_GA_SA_B64` (base64 of the JSON key), or `PICKSHELF_GA_SA_JSON` |

**The tag isn't in the HTML.** `analytics.js` adds `gtag/js?id=…` at runtime, so grepping the page
source for `gtag` or `G-` finds nothing. To check the tag, look for `analytics.js?v=` in the page,
or look for data in GA.

Events: GA's automatic ones, plus
- `link_click` on every tap, with params `link_type` (partner/outbound/internal), `partner`,
  `item_no`, `item_name`, `button`, `link_url`
- `search` with the search-box text (sent after a 1.5 s pause)

The custom dimensions for those params were registered on **2026-10-24** (`--setup`). They don't
apply retroactively, so earlier clicks show `(not set)` for partner and item.

### Reports: `scripts/ga_report.py`

```bash
pip install google-auth requests
python3 scripts/ga_report.py                 # last 28 days, bots excluded
python3 scripts/ga_report.py --days 7 --rows 30
python3 scripts/ga_report.py --json          # raw data for further analysis
python3 scripts/ga_report.py --include-bots
python3 scripts/ga_report.py --key key.json  # local key file instead of env
```

On Windows, run with `python -X utf8` or the Korean output fails on cp949.

**Bot filter.** A session counts as a bot if either rule matches:
1. Headless browser: square or odd resolution (`BOT_RESOLUTIONS`) and no referrer.
2. Meta link-preview crawler: source `facebook.com`/`m.facebook.com` from outside KR. When a link is
   posted on Threads/Instagram, Meta fetches it from US/IE/SE data centres (2000x2000 or 412x915).
   pickshelf isn't posted on Facebook. On 2026-10-24 this was about 1/3 of all "visitors".

Datacentre towns in GA's city list (Prineville, Altoona, Forest City, Boardman, Dublin) are a
sign that new crawler traffic has slipped past the filter.

**Key rotation.** Google never lets you download an existing key's JSON again. If the file is lost,
create a new key on the same service account (GA access stays as is), then update
`PICKSHELF_GA_SA_B64`. The key file the owner saved is kept in their own Google Cloud storage,
not in this repo. Never commit a key.

## Findings so far (2026-10-23 ~ 24, ~45 real sessions)

- Threads brings the most visits but mostly lands on `/travel/` and bounces (engagement ~16%).
- Instagram (`link_in_bio`) to `/hotels/` performs best: long dwell, most link clicks.
- Search terms with no matching content: 히로시마, 암스테르담, 브뤼셀.
