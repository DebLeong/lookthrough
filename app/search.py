"""Search layer.

Telem is the primary retrieval layer (routing across ~11 engines, platform
providers, fetch with fallback, monitors, session tracing). Tavily-direct is
used for bulk adverse-media sweeps to stretch the Telem budget.

All calls are cached on disk and logged to the ledger with an estimated cost.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .cache import cached, ledger
from .config import TAVILY_API_KEY, TELEM_API_KEY, TELEM_BASE_URL

# Pinned-only platform providers (auto-routing never selects these).
PLATFORM_PROVIDERS = {
    "linkedin": "apify_linkedin",
    "wechat": "socialdatax_wechat",
    "gmaps": "outscraper_gmaps",
}

# Rough per-call cost estimates for the budget meter (USD). Telem passes through
# upstream rates; $20 ~= 4000 queries => ~$0.005/provider run on average.
EST_COST = {"telem_search_run": 0.005, "telem_platform": 0.01, "telem_fetch": 0.004, "tavily_credit": 0.008}


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


@dataclass
class Hit:
    url: str
    title: str
    snippet: str
    engine: str          # which upstream engine returned it (exa, brave, tavily, ...)
    via: str             # "telem" | "tavily"
    published: str | None = None
    query: str = ""

    @property
    def domain(self) -> str:
        return domain(self.url)

    def to_dict(self) -> dict:
        return {**self.__dict__, "domain": self.domain}


@dataclass
class Page:
    url: str
    title: str
    content: str
    sha256: str | None
    provider: str
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Meter:
    """Per-run spend + routing telemetry, surfaced in the UI."""
    budget_usd: float
    spent_usd: float = 0.0
    calls: int = 0
    cache_hits: int = 0
    engines: dict[str, int] = field(default_factory=dict)
    session_id: str | None = None
    offline: bool = False
    routes: list = field(default_factory=list)

    def charge(self, usd: float, hit: bool) -> None:
        self.calls += 1
        if hit:
            self.cache_hits += 1
        else:
            self.spent_usd += usd

    @property
    def exhausted(self) -> bool:
        return self.spent_usd >= self.budget_usd

    def to_dict(self) -> dict:
        return {"budget_usd": self.budget_usd, "spent_usd": round(self.spent_usd, 4), "calls": self.calls,
                "cache_hits": self.cache_hits, "engines": self.engines, "session_id": self.session_id,
                "routes": self.routes[-20:]}


class SearchClient:
    """Telem first. If Telem auth is down (hackathon key activation), degrade to
    Tavily-direct so development continues; the UI shows the degraded state."""

    def __init__(self, meter: Meter):
        self.meter = meter
        self._telem = None
        self._tavily = None
        self.telem_down: str | None = None

    def search(self, query: str, **kw) -> list[Hit]:
        if not self.telem_down:
            try:
                return self.telem_search(query, **kw)
            except LookupError:
                raise
            except Exception as e:  # auth / network: degrade, remember why
                if "Invalid API key" in str(e) or "401" in str(e) or "AuthError" in type(e).__name__:
                    self.telem_down = f"Telem unavailable: {e}"
                else:
                    raise
        return self.tavily_search(query, max_results=kw.get("num_results", 5), end_date=kw.get("published_before"))

    def platform(self, platform: str, query: str, num_results: int = 5, published_before: str | None = None) -> list[Hit]:
        if self.telem_down:
            return []
        try:
            return self.platform_search(platform, query, num_results, published_before)
        except LookupError:
            raise
        except Exception as e:
            ledger({"kind": "platform_error", "platform": platform, "err": str(e)[:300]})
            return []

    def read(self, urls: list[str]) -> list[Page]:
        if not self.telem_down:
            try:
                return self.fetch(urls)
            except LookupError:
                raise
            except Exception as e:
                if "Invalid API key" in str(e) or "AuthError" in type(e).__name__:
                    self.telem_down = f"Telem unavailable: {e}"
                else:
                    raise
        return self.tavily_extract(urls)

    def tavily_extract(self, urls: list[str]) -> list[Page]:
        import hashlib

        def call():
            r = self.tavily.extract(urls, extract_depth="basic", include_usage=True)
            return r

        data, hit = cached("tavily_extract", {"u": urls}, call, offline=self.meter.offline)
        self.meter.charge(EST_COST["tavily_credit"] * max(1, len(urls) // 5), hit)
        pages = []
        got = {x["url"]: x for x in data.get("results", [])}
        for u in urls:
            x = got.get(u)
            txt = (x or {}).get("raw_content") or ""
            pages.append(Page(u, "", txt[:20000], hashlib.sha256(txt.encode()).hexdigest() if txt else None,
                              "tavily-extract", bool(txt), None if txt else "extract failed"))
        return pages

    # ---- clients -------------------------------------------------------
    @property
    def telem(self):
        if self._telem is None:
            from telem import Telem
            if not TELEM_API_KEY:
                raise RuntimeError("TELEM_API_KEY missing in .env")
            self._telem = Telem(api_key=TELEM_API_KEY, base_url=TELEM_BASE_URL, timeout=90)
        return self._telem

    @property
    def tavily(self):
        if self._tavily is None:
            from tavily import TavilyClient
            if not TAVILY_API_KEY:
                raise RuntimeError("TAVILY_API_KEY missing in .env")
            self._tavily = TavilyClient(api_key=TAVILY_API_KEY)
        return self._tavily

    # ---- Telem search ---------------------------------------------------
    def telem_search(self, query: str, *, providers: list[str] | None = None, auto: bool = True,
                     tier: str = "extended", num_results: int = 5, include_domains: list[str] | None = None,
                     published_after: str | None = None, published_before: str | None = None) -> list[Hit]:
        payload = {"q": query, "p": providers, "auto": auto, "tier": tier, "n": num_results,
                   "d": include_domains, "after": published_after, "before": published_before}

        def call():
            kw: dict[str, Any] = {"tier": tier, "num_results": num_results}
            if providers:
                kw["providers_include"] = providers
            if auto and not _is_platform(providers):
                kw["auto_routing"] = "accuracy"
            if include_domains:
                kw["include_domains"] = include_domains
            if published_after:
                kw["published_after"] = published_after
            if published_before:
                kw["published_before"] = published_before
            if self.meter.session_id:
                kw["session"] = self.meter.session_id
            t0 = time.time()
            resp = self.telem.search(query, **kw)
            runs = [{"provider": r.provider, "status": r.status, "latency_ms": r.latency_ms,
                     "results": [{"url": x.url, "title": x.title, "summary": x.summary or " ".join(x.excerpt or []),
                                  "publish_date": x.publish_date} for x in r.results]}
                    for r in resp.by_provider]
            ledger({"kind": "telem_search", "q": query, "providers": [r["provider"] for r in runs],
                    "latency_s": round(time.time() - t0, 2)})
            return {"session_id": resp.session_id, "runs": runs,
                    "routing": resp.raw.get("routing") if isinstance(resp.raw, dict) else None}

        data, hit = cached("telem_search", payload, call, offline=self.meter.offline)
        ok_runs = [r for r in data["runs"] if r["status"] in ("ok", "succeeded", "success", "completed") or r["results"]]
        unit = EST_COST["telem_platform"] if _is_platform(providers) else EST_COST["telem_search_run"]
        self.meter.charge(unit * max(1, len(ok_runs)), hit)
        if not self.meter.session_id and data.get("session_id"):
            self.meter.session_id = data["session_id"]
        for rt in data.get("routing") or []:
            self.meter.routes.append({"q": query, "topic": rt.get("topic"), "providers": rt.get("providers")})
        hits = []
        for r in data["runs"]:
            if r["results"]:
                self.meter.engines[r["provider"]] = self.meter.engines.get(r["provider"], 0) + 1
            for x in r["results"]:
                if x["url"]:
                    hits.append(Hit(x["url"], x["title"] or "", x["summary"] or "", r["provider"], "telem",
                                    x.get("publish_date"), query))
        return hits

    def platform_search(self, platform: str, query: str, num_results: int = 5,
                        published_before: str | None = None) -> list[Hit]:
        return self.telem_search(query, providers=[PLATFORM_PROVIDERS[platform]], auto=False, tier="default",
                                 num_results=num_results, published_before=published_before)

    # ---- Telem fetch ----------------------------------------------------
    def fetch(self, urls: list[str], max_chars: int = 20000) -> list[Page]:
        pages: list[Page] = []
        for i in range(0, len(urls), 5):  # Telem caps 5 URLs per fetch
            batch = urls[i:i + 5]

            def call(batch=batch):
                kw: dict[str, Any] = {"inline_max_chars": max_chars}
                if self.meter.session_id:
                    kw["session"] = self.meter.session_id
                resp = self.telem.fetch(batch, **kw)
                out = []
                for r in resp.results:
                    raw = r.raw if isinstance(r.raw, dict) else {}
                    sha = raw.get("content_sha256") or (r.provider_metadata or {}).get("content_sha256")
                    out.append({"url": r.url, "title": r.title, "content": r.content or "", "sha256": sha,
                                "provider": r.provider, "ok": bool(r.content) and not r.error,
                                "error": (r.error or {}).get("message") if r.error else None})
                ledger({"kind": "telem_fetch", "urls": batch, "ok": sum(o["ok"] for o in out)})
                return out

            data, hit = cached("telem_fetch", {"u": batch, "m": max_chars}, call, offline=self.meter.offline)
            self.meter.charge(EST_COST["telem_fetch"] * sum(1 for d in data if d["ok"]), hit)
            pages += [Page(**d) for d in data]
        for p in pages:
            if p.ok and not p.sha256:
                import hashlib
                p.sha256 = hashlib.sha256(p.content.encode()).hexdigest()
        return pages

    # ---- Tavily direct (bulk adverse media) -----------------------------
    def tavily_search(self, query: str, *, topic: str = "general", depth: str = "basic", max_results: int = 5,
                      time_range: str | None = None, end_date: str | None = None) -> list[Hit]:
        payload = {"q": query, "topic": topic, "depth": depth, "n": max_results, "tr": time_range, "end": end_date,
                   "v": 2}

        def call():
            kw: dict[str, Any] = {"topic": topic, "search_depth": depth, "max_results": max_results,
                                  "include_usage": True}
            if time_range:
                kw["time_range"] = time_range
            if end_date:
                kw["end_date"] = end_date
            kw["include_published_date"] = True
            r = self.tavily.search(query, **kw)
            ledger({"kind": "tavily_search", "q": query, "credits": (r.get("usage") or {}).get("credits")})
            return r

        data, hit = cached("tavily_search", payload, call, offline=self.meter.offline)
        credits = (data.get("usage") or {}).get("credits") or (2 if depth == "advanced" else 1)
        self.meter.charge(EST_COST["tavily_credit"] * credits, hit)
        self.meter.engines["tavily-direct"] = self.meter.engines.get("tavily-direct", 0) + 1
        return [Hit(x["url"], x.get("title", ""), x.get("content", ""), "tavily", "tavily",
                    x.get("published_date"), query) for x in data.get("results", [])]


def _is_platform(providers: list[str] | None) -> bool:
    return bool(providers) and all(p in PLATFORM_PROVIDERS.values() for p in providers)
