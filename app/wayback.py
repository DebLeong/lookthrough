"""Point-in-time page snapshots via the Internet Archive CDX API.

For an as-of reconstruction, an undated page can only be admitted if we read
the version that existed on or before the as-of date.
"""
from __future__ import annotations

import httpx

from .cache import cached


def snapshot_url(url: str, as_of: str) -> str | None:
    """Return a raw Wayback snapshot URL captured on/before as_of (YYYY-MM-DD), or None."""
    ts = as_of.replace("-", "")

    def call():
        try:
            r = httpx.get("http://web.archive.org/cdx/search/cdx",
                          params={"url": url, "to": ts, "limit": "-1", "output": "json",
                                  "filter": "statuscode:200", "fl": "timestamp,original"}, timeout=20)
            rows = r.json() if r.status_code == 200 and r.text.strip() else []
        except (httpx.HTTPError, ValueError):
            return None
        if len(rows) < 2:
            return None
        stamp, original = rows[-1]
        return {"ts": stamp, "original": original}

    hit, _ = cached("wayback", {"u": url, "to": ts}, call)
    if not hit or hit["ts"][:8] > ts:
        return None
    return f"https://web.archive.org/web/{hit['ts']}id_/{hit['original']}"


def snapshot_date(wayback_url: str) -> str | None:
    try:
        stamp = wayback_url.split("/web/")[1][:8]
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
    except IndexError:
        return None
