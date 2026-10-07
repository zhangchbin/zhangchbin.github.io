#!/usr/bin/env python3
"""Fetch Google Scholar total citations and update index.html.

The number is floored to the nearest 100 (e.g. 2321 -> 2300) and written into
the <span id="gs-citations-en"> and <span id="gs-citations-cn"> elements.
"""
import json
import re
import sys
from pathlib import Path

import urllib.request
import urllib.error

USER_ID = "3nFfqMIAAAAJ"
INDEX = Path(__file__).resolve().parent.parent / "index.html"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def from_badge_service():
    """Primary source: third-party Shields endpoint (uses SerpApi -> Google Scholar)."""
    url = f"https://google-scholar-badge.vercel.app/citations?user={USER_ID}"
    data = json.loads(fetch_url(url))
    msg = str(data.get("message", "")).replace(",", "")
    m = re.search(r"\d+", msg)
    if not m:
        raise ValueError(f"badge service returned no number: {data}")
    return int(m.group(0))


def from_google_scholar():
    """Fallback: scrape the Google Scholar profile page directly."""
    url = f"https://scholar.google.com/citations?user={USER_ID}&hl=en"
    html = fetch_url(url)
    # The total citations is the first <td class="gsc_rsb_std">NNN</td>.
    cells = re.findall(r'gsc_rsb_std">([0-9,]+)</td>', html)
    if not cells:
        raise ValueError("could not locate citation count on Scholar page")
    return int(cells[0].replace(",", ""))


def fetch_citations():
    for fn in (from_badge_service, from_google_scholar):
        try:
            n = fn()
            if n > 0:
                return n
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} failed: {e}", file=sys.stderr)
    raise RuntimeError("all citation sources failed")


def update_index(total):
    rounded = (total // 100) * 100
    en = f"{rounded:,}"          # 2,300
    cn = str(rounded)            # 2300
    text = INDEX.read_text(encoding="utf-8")

    new = re.sub(r'(<span id="gs-citations-en">)[^<]*(</span>)',
                 rf'\g<1>{en}\g<2>', text)
    new = re.sub(r'(<span id="gs-citations-cn">)[^<]*(</span>)',
                 rf'\g<1>{cn}\g<2>', new)

    if new == text:
        print(f"No change (still {en} / {cn}).")
        return False
    INDEX.write_text(new, encoding="utf-8")
    print(f"Updated citations -> {en} (raw total {total}).")
    return True


def main():
    total = fetch_citations()
    changed = update_index(total)
    print(f"raw_total={total} rounded={(total // 100) * 100} changed={changed}")
    sys.exit(0)


if __name__ == "__main__":
    main()
