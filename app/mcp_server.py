"""LookThrough MCP server: time-travel search primitives for any agent.

Tools
  time_travel_search(query, as_of)  Telem-routed search restricted to what was public on/before as_of
  verify_quote(url, quote, as_of)   is this exact quote on the page (or its archived as-of version)?
  screen_entity(name, as_of)        watchlist hits with severity tier and listing date, as of a date

Register with Claude Code:
  claude mcp add lookthrough -- /path/to/.venv/bin/python -m app.mcp_server
(run from the repo root, or pass --cwd). Never prints to stdout: stdio is the MCP channel.
"""
from __future__ import annotations

import re
from datetime import date

from mcp.server.mcpserver import MCPServer
from rapidfuzz import fuzz

from .agent import mentions_future, norm_date
from .config import RUN_BUDGET_USD
from .screening import watchlist
from .search import Meter, SearchClient
from .wayback import snapshot_date, snapshot_url

server = MCPServer(
    name="lookthrough",
    instructions=(
        "Time-travel search. Use time_travel_search with as_of=YYYY-MM-DD to see only what was public on that "
        "date (no future leakage). Cite only quotes that verify_quote confirms. Use screen_entity for sanctions "
        "and government-list exposure as of a date. Screening signals are not legal advice."),
)


def _client() -> SearchClient:
    return SearchClient(Meter(budget_usd=RUN_BUDGET_USD))


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


@server.tool()
def time_travel_search(query: str, as_of: str | None = None, max_sources: int = 6, read_pages: bool = True) -> dict:
    """Search the web through Telem's multi-engine router, restricted to what was publicly knowable on `as_of`
    (YYYY-MM-DD). Dated sources after as_of are dropped; undated pages are only admitted via an Internet Archive
    snapshot captured on/before as_of. Omit as_of for a normal (today) search. Returns dated, hashed sources with
    the engines that found them, Telem's routing decision and how many later sources were excluded."""
    as_of = norm_date(as_of) if as_of else None
    sc = _client()
    hits = sc.search(query, num_results=5, published_before=as_of)
    by_url: dict[str, list] = {}
    for h in hits:
        by_url.setdefault(h.url.split("#")[0].rstrip("/"), []).append(h)
    ranked = sorted(by_url.items(), key=lambda kv: -len({h.engine for h in kv[1]}))   # cross-engine consensus

    admitted, excluded = [], 0
    for url, hs in ranked:
        d = min([x for x in (norm_date(h.published) for h in hs) if x] or [None], key=lambda x: x or "")
        item = {"url": url, "title": hs[0].title, "date": d, "engines": sorted({h.engine for h in hs}),
                "snippet": _clean(hs[0].snippet)[:400], "snapshot": None, "read_url": url}
        if as_of:
            if d and d > as_of:
                excluded += 1
                continue
            if not d:
                snap = snapshot_url(url, as_of)
                if not snap:
                    excluded += 1
                    continue
                item.update(snapshot=snap, read_url=snap, date=snapshot_date(snap))
        admitted.append(item)
        if len(admitted) >= max_sources:
            break

    if read_pages and admitted:
        pages = {p.url.rstrip("/"): p for p in sc.read([a["read_url"] for a in admitted])}
        for a in admitted:
            p = pages.get(a["read_url"].rstrip("/"))
            a["excerpt"] = _clean(p.content)[:1500] if p and p.ok else None
            a["sha256"] = p.sha256 if p and p.ok else None
    if as_of:   # layer 3: content scan, since provider publish dates can be wrong
        clean = []
        for a in admitted:
            yr = mentions_future((a.get("excerpt") or "") + " " + a["snippet"], as_of)
            if yr:
                excluded += 1
                continue
            clean.append(a)
        admitted = clean
    for a in admitted:
        a.pop("read_url", None)

    return {"query": query, "as_of": as_of or date.today().isoformat(), "time_bounded": bool(as_of),
            "sources": admitted, "excluded_after_as_of": excluded,
            "routing": sc.meter.routes[-1:] or None, "engines_used": sc.meter.engines,
            "telem_session": sc.meter.session_id, "est_cost_usd": round(sc.meter.spent_usd, 4),
            "degraded": sc.telem_down}


@server.tool()
def verify_quote(url: str, quote: str, as_of: str | None = None) -> dict:
    """Check that `quote` actually appears on the page at `url` (exact or near-exact match, whitespace/case
    insensitive). With as_of, checks the Internet Archive version captured on/before that date instead of today's
    page. Use this before citing any claim."""
    as_of = norm_date(as_of) if as_of else None
    target, snap_d = url, None
    if as_of:
        snap = snapshot_url(url, as_of)
        if snap:
            target, snap_d = snap, snapshot_date(snap)
    pages = _client().read([target])
    p = pages[0] if pages else None
    if not p or not p.ok:
        return {"verified": False, "reason": "page could not be read", "url": url, "checked": target}
    hay, needle = _clean(p.content).lower(), _clean(quote).lower()
    exact = needle in hay
    score = 100.0 if exact else float(fuzz.partial_ratio(needle, hay))
    i = hay.find(needle[:40]) if exact else -1
    return {"verified": exact or score >= 90, "match": "exact" if exact else ("near" if score >= 90 else "none"),
            "score": round(score, 1), "url": url, "checked": target, "snapshot_date": snap_d,
            "sha256": p.sha256, "context": _clean(p.content)[max(0, i - 120): i + len(needle) + 120] if i >= 0 else None}


@server.tool()
def screen_entity(name: str, as_of: str | None = None, country: str | None = None) -> dict:
    """Screen a company or person against consolidated watchlists (OFAC SDN, DoD 1260H, BIS Entity List, UN, UK,
    EU, ...). Each hit has a severity tier: 'binding' (legal prohibition e.g. OFAC SDN, NS-CMIC) vs 'restrictive'
    (e.g. 1260H is a Pentagon procurement ban, NOT an investment ban) and its listing date. With as_of, only
    listings in force by that date count. country: ISO-2 code to reduce false positives."""
    as_of = norm_date(as_of) if as_of else None
    hits = watchlist().screen(name, countries=[country.lower()] if country else None, as_of=as_of)
    return {"name": name, "as_of": as_of or date.today().isoformat(),
            "hits": [{"listed_name": h.name, "match_score": h.score, "tier": h.tier, "listed_since": h.listed_since,
                      "what_it_means": h.label, "countries": h.countries} for h in hits],
            "note": "Name matches are candidates for review, not determinations."}


if __name__ == "__main__":
    server.run("stdio")
