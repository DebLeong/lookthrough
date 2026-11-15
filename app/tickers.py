"""Ticker -> company name resolution via Telem search (no extra data vendor needed).

"SMCI" -> "Super Micro Computer, Inc."; also works for "0700.HK"-style tickers.
Reads finance-site titles of the form "Company Name (TICKER)" and picks the most common name.
"""
from __future__ import annotations

import re
from collections import Counter

from .cache import cached
from .config import RUN_BUDGET_USD
from .search import Meter, SearchClient

_TICKER = re.compile(r"^\$?([A-Za-z]{1,5}|\d{1,5}\.[A-Za-z]{1,3}|[A-Za-z]{1,5}\.[A-Za-z]{1,3})$")


def looks_like_ticker(s: str) -> bool:
    return bool(_TICKER.match(s.strip()))


def resolve(text: str) -> tuple[str, str | None]:
    """Return (name_to_search, resolved_note). Non-tickers pass through unchanged."""
    raw = text.strip()
    if not looks_like_ticker(raw):
        return raw, None
    tk = raw.lstrip("$").upper()

    def call():
        sc = SearchClient(Meter(budget_usd=RUN_BUDGET_USD))
        hits = sc.search(f"{tk} stock ticker company name", num_results=8)
        pat = re.compile(r"([A-Z][\w&.,'\- ]{2,80}?)\s*\(\s*(?:[A-Z]+\s*:\s*)?\^?" + re.escape(tk) + r"\s*\)")
        names = Counter()
        for h in hits:
            for m in pat.finditer(f"{h.title} {h.snippet}"):
                n = re.sub(r"\s+", " ", m.group(1)).strip(" -,")
                if 3 <= len(n) <= 80 and not n.lower().startswith(("stock", "shares", "ticker")):
                    names[n] += 1
        return names.most_common(1)[0][0] if names else None

    name, _ = cached("ticker", {"t": tk}, call)
    if not name:
        return raw, None
    return name, f"Resolved ticker {tk} → {name}"
