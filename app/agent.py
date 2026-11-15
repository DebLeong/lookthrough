"""LookThrough agent: recursive, evidence-grounded, time-aware exposure graph.

Per entity:
  1. Retrieve    — Telem auto-routed web search (multi-engine, publish dates) + Tavily sweep
                   + pinned platform providers (WeChat, LinkedIn)
  2. Rank        — cross-engine consensus: URLs returned by more engines/queries first
  3. Admit       — in as-of mode, only sources published on/before the as-of date, or a
                   Wayback snapshot captured on/before it (undated live pages are excluded)
  4. Read        — Telem Fetch (fallback across fetchers), sha256 per page snapshot
  5. Extract     — LLM pulls facts, relationships and dated stakeholder events, each with a
                   verbatim quote + source id
  6. Verify      — every quote is checked against the fetched text; unverified claims dropped
  7. Screen      — watchlists with severity tiers and listing dates, outbound-rule rules engine,
                   policy exclusions, adverse media; every flag carries "knowable since"
  8. Expand      — pick next nodes by ownership %, risk, depth and remaining budget
After the walk: OFAC 50% aggregation over ownership edges; a dated timeline of signals and
stakeholder actions (what was knowable when, and what people did anyway).
"""
from __future__ import annotations

import json
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Callable

from rapidfuzz import fuzz

from . import llm
from .config import LLM_SMART_MODEL, RUN_BUDGET_USD, RUNS_DIR
from .rules import ofac_50, oisp_assessment
from .screening import normalize, watchlist
from .search import Hit, Meter, Page, SearchClient, domain
from .wayback import snapshot_date, snapshot_url

Emit = Callable[[dict], None]

COUNTRY_HINT = "Use ISO-3166 alpha-2 lowercase country codes (cn, hk, sg, us, ky for Cayman, vg for BVI...)."
CONCERN = {"cn", "hk", "mo", "ru", "ir", "kp", "cu", "ve"}

_GENERIC = re.compile(r"^(the )?(founding |management |leadership |executive )?(team|founders?|investors?|"
                      r"shareholders?|employees|management|board|public|undisclosed|others?|various|angel investors?)$", re.I)
_ISO = re.compile(r"((?:19|20)\d{2})-(\d{2})(?:-(\d{2}))?")


def _generic(name: str) -> bool:
    n = re.sub(r"\(.*?\)", "", name).strip()
    low = n.lower()
    return (len(n) < 3 or bool(_GENERIC.match(n)) or "," in n and len(n.split(",")) > 2
            or low.startswith(("undisclosed", "unnamed", "several ", "founding team", "founders ", "existing investors",
                               "other investors", "management team", "employees")))


def norm_date(s) -> str | None:
    """Best-effort publish date -> YYYY-MM-DD (None when unknown)."""
    if not s:
        return None
    s = str(s).strip()
    out = None
    m = _ISO.search(s)
    if m:
        out = f"{m.group(1)}-{m.group(2)}-{m.group(3) or '01'}"
    else:
        try:
            out = parsedate_to_datetime(s).date().isoformat()
        except (TypeError, ValueError, IndexError):
            return None
    # reject epoch placeholders and future dates
    return out if "1980-01-01" <= out <= date.today().isoformat() else None


_YEAR = re.compile(r"\b(19[89]\d|20\d\d)\b")


def mentions_future(text: str, as_of: str | None) -> str | None:
    """Content-level leakage check: does the text mention a year after the as-of date?
    Provider publish dates can be wrong, so dated sources are re-checked by content."""
    if not as_of or not text:
        return None
    cutoff = int(as_of[:4])
    later = sorted({int(y) for y in _YEAR.findall(text) if int(y) > cutoff})
    return str(later[0]) if later else None


def _min_date(ds) -> str | None:
    ds = [d for d in ds if d]
    return min(ds) if ds else None


@dataclass
class Evidence:
    url: str
    domain: str
    quote: str
    engines: list[str]
    sha256: str | None = None
    date: str | None = None          # publish date (or snapshot date) of the source
    snapshot: str | None = None      # Wayback snapshot URL when used

    def to_dict(self):
        return dict(self.__dict__)


@dataclass
class Node:
    id: str
    name: str
    kind: str = "company"          # company | fund | person
    depth: int = 0
    status: str = "queued"         # queued | researching | done | screened
    facts: dict = field(default_factory=dict)
    flags: list[dict] = field(default_factory=list)
    risk: str = "none"             # none | amber | red
    sources: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    direction: str = "root"        # root | up (owners/investors chain) | down (subsidiaries/portfolio)

    def to_dict(self):
        return dict(self.__dict__)


class LookThrough:
    def __init__(self, root: str, *, policy: str = "", max_depth: int = 2, max_nodes: int = 8,
                 budget_usd: float = RUN_BUDGET_USD, offline: bool = False, emit: Emit | None = None,
                 root_kind: str = "company", as_of: str | None = None):
        self.root_name = root.strip()
        self.root_kind = root_kind
        self.policy = policy.strip()
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.as_of = norm_date(as_of) if as_of else None
        self.meter = Meter(budget_usd=budget_usd, offline=offline)
        self.sc = SearchClient(self.meter)
        self.emit = emit or (lambda e: None)
        self.nodes: dict[str, Node] = {}
        self.edges: list[dict] = []
        self.timeline: list[dict] = []
        slug = re.sub(r"[^a-z0-9]+", "-", self.root_name.lower()).strip("-")
        self.run_id = f"{slug}{'-asof-' + self.as_of if self.as_of else ''}-{uuid.uuid4().hex[:6]}"
        self.started = time.time()
        self.events: list[dict] = []
        self.excluded_sources = 0
        self.policy_rules = self._compile_policy()

    # ------------------------------------------------------------------ utils
    def _ev(self, type_: str, **kw):
        evt = {"type": type_, "t": round(time.time() - self.started, 2), **kw}
        if type_ != "done":
            self.events.append(json.loads(json.dumps(evt, default=str)))
        self.emit(evt)

    def _log(self, msg: str, node: str | None = None):
        self._ev("log", msg=msg, node=node)

    def _meter(self):
        self._ev("meter", meter=self.meter.to_dict(), telem_down=self.sc.telem_down)

    def _key(self, name: str) -> str:
        return normalize(name) or name.lower()

    def _find(self, name: str) -> Node | None:
        k = self._key(name)
        if k in self.nodes:
            return self.nodes[k]
        for nk, n in self.nodes.items():
            if fuzz.token_sort_ratio(k, nk) >= 92:
                return n
        return None

    def _add_node(self, name: str, kind: str, depth: int) -> Node:
        existing = self._find(name)
        if existing:
            return existing
        n = Node(id=self._key(name), name=name, kind=kind, depth=depth)
        self.nodes[n.id] = n
        self._ev("node", node=n.to_dict())
        return n

    def _add_edge(self, src: Node, dst: Node, type_: str, pct: float | None, evidence: list[Evidence], label=""):
        for e in self.edges:
            if e["src"] == src.id and e["dst"] == dst.id and e["type"] == type_:
                return
        e = {"src": src.id, "dst": dst.id, "type": type_, "pct": pct, "label": label,
             "evidence": [x.to_dict() for x in evidence],
             "known_since": _min_date(x.date for x in evidence),
             "corroboration": len({x.domain for x in evidence})}
        self.edges.append(e)
        self._ev("edge", edge=e)

    # ------------------------------------------------------------- policy
    def _compile_policy(self) -> list[dict]:
        if not self.policy:
            return []
        try:
            rules = llm.complete_json(
                "Compile this investment-compliance policy into screening rules.\n"
                f"POLICY:\n{self.policy}\n\n"
                'Return JSON: {"rules":[{"id":"short_snake_id","category":"human label",'
                '"what_counts":"one sentence: business activities that trigger it",'
                '"threshold":"e.g. any involvement | >5% revenue | n/a"}]}. '
                "Skip sanctions/outbound-investment items (handled by dedicated engines); keep exclusions like "
                "weapons, firearms, tobacco, coal, surveillance, gambling, PEP, etc.")
            return rules.get("rules", [])
        except llm.LLMError as e:
            self._log(f"policy compile failed: {e}")
            return []

    # ----------------------------------------------------------- retrieval
    def _retrieve(self, node: Node) -> tuple[list[Hit], dict[str, list[Hit]]]:
        name = node.name
        if node.kind == "fund":
            queries = [f"{name} portfolio companies investments", f"{name} invested in startups list portfolio",
                       f"{name} led funding round 2025"]
        elif node.kind == "person":
            queries = [f"{name} biography companies roles"]
        else:
            queries = [f"{name} company headquarters founders incorporation",
                       f"{name} parent company shareholders subsidiaries ownership"]
            if node.depth == 0:
                queries.append(f"{name} funding round raised Series investors led by")
        hits: list[Hit] = []
        for q in queries:
            if self.meter.exhausted:
                break
            n_routes = len(self.meter.routes)
            hits += self.sc.search(q, num_results=5, published_before=self.as_of)
            for rt in self.meter.routes[n_routes:]:
                self._log(f"Telem routed '{q[:48]}' as topic '{rt['topic']}' -> {', '.join(rt['providers'] or [])}", node.id)
            self._meter()
        if not self.meter.exhausted and node.kind != "person" and node.depth == 0:
            # Red-flag sweep on the target: the questions a diligence analyst asks first.
            for q in (f"{name} short seller report fraud allegations",
                      f"{name} auditor resigned restatement SEC investigation",
                      f"{name} lawsuit DOJ probe regulator fine"):
                if self.meter.exhausted:
                    break
                hits += self.sc.search(q, num_results=5, published_before=self.as_of)
            self._meter()
        if not self.meter.exhausted and node.kind != "person":
            hits += self.sc.tavily_search(
                f'"{name}" sanctions OR investigation OR Treasury OR fraud OR export controls OR military OR acquisition',
                topic="general", max_results=5, end_date=self.as_of)
            self._meter()
        platform: dict[str, list[Hit]] = {}
        if node.kind == "company" and not self.meter.exhausted:
            # Pinned platform providers: never chosen by auto-routing, so we call them deliberately.
            platform["wechat"] = self.sc.platform("wechat", name, 5, self.as_of)    # Chinese-language evidence
            platform["linkedin"] = self.sc.platform("linkedin", f"{name} company", 5, self.as_of)
            got = {k: len(v) for k, v in platform.items()}
            self._log(f"Platform search: WeChat {got['wechat']} articles, LinkedIn {got['linkedin']} results", node.id)
            self._meter()
        return hits, platform

    def _rank(self, hits: list[Hit]) -> list[tuple[str, list[Hit]]]:
        """Cross-engine consensus ranking with a domain-diversity penalty."""
        by_url: dict[str, list[Hit]] = defaultdict(list)
        for h in hits:
            by_url[h.url.split("#")[0].rstrip("/")].append(h)
        seen_domains: dict[str, int] = defaultdict(int)

        def score(item):
            _url, hs = item
            return len({h.engine for h in hs}) * 2 + len({h.query for h in hs}) - 0.1 * seen_domains[hs[0].domain]

        ranked, pool = [], dict(by_url)
        while pool:
            best = max(pool.items(), key=score)
            ranked.append(best)
            seen_domains[best[1][0].domain] += 1
            del pool[best[0]]
        return ranked

    def _admit(self, ranked) -> list[dict]:
        """Decide, per URL, what we may read and how it is dated.
        Live mode: everything. As-of mode: dated <= as_of, or a Wayback snapshot <= as_of."""
        out = []
        for url, hs in ranked:
            d = _min_date(norm_date(h.published) for h in hs)
            item = {"url": url, "hits": hs, "date": d, "read_url": url, "snapshot": None}
            if self.as_of:
                if d and d <= self.as_of:
                    pass
                elif d and d > self.as_of:
                    self.excluded_sources += 1
                    continue
                else:
                    snap = snapshot_url(url, self.as_of) if len(out) < 8 else None
                    if not snap:
                        self.excluded_sources += 1
                        continue
                    item.update(read_url=snap, snapshot=snap, date=snapshot_date(snap))
            out.append(item)
        return out

    # ---------------------------------------------------------- extraction
    def _extract(self, node: Node, admitted: list[dict], pages: dict[str, Page], platform: dict[str, list[Hit]]) -> dict:
        blocks, src_index = [], {}
        for i, a in enumerate(admitted[:14]):
            sid = f"S{i + 1}"
            hs = a["hits"]
            p = pages.get(a["read_url"])
            snippets = " ".join(h.snippet for h in hs)
            body = (p.content[:3500] if p and p.ok else "") or snippets[:1200]
            src_index[sid] = {"url": a["url"], "text": body + " " + snippets, "engines": sorted({h.engine for h in hs}),
                              "sha256": p.sha256 if p else None, "domain": hs[0].domain, "date": a["date"],
                              "snapshot": a["snapshot"]}
            dated = f"Published: {a['date']}" if a["date"] else "Published: unknown"
            if a["snapshot"]:
                dated = f"Archived snapshot from {a['date']}"
            blocks.append(f"[{sid}] {hs[0].title}\nURL: {a['url']}\n{dated}\n{body}")
        for plat, hs in platform.items():
            for j, h in enumerate(hs[:5]):
                d = norm_date(h.published)
                if self.as_of and (not d or d > self.as_of):
                    continue
                sid = f"{plat.upper()[:2]}{j + 1}"
                src_index[sid] = {"url": h.url, "text": f"{h.title} {h.snippet}", "engines": [h.engine],
                                  "sha256": None, "domain": h.domain, "date": d, "snapshot": None}
                blocks.append(f"[{sid}] ({plat}) {h.title}\nURL: {h.url}\nPublished: {d or 'unknown'}\n{h.snippet[:900]}")

        policy_txt = "\n".join(f'- {r["id"]}: {r["category"]} — {r["what_counts"]} ({r["threshold"]})'
                               for r in self.policy_rules) or "(none)"
        kind_specific = {
            "fund": '"portfolio":[{"name":"","country":"","sector":"","quote":"","src":"S1"}],',
        }.get(node.kind, "")
        as_of_txt = (f"\nASSESSMENT DATE: {self.as_of}. Report only what was known on or before this date. "
                     f"Ignore any statement about events after {self.as_of}.\n") if self.as_of else ""
        prompt = f"""You are a compliance analyst doing look-through due diligence on: "{node.name}" ({node.kind}).
Read the numbered sources and extract ONLY facts stated in them. Every fact needs a short VERBATIM quote
(copied exactly, 5-25 words) and the source id. If a fact is not in the sources, use null / empty list.
Ignore sources about a different entity with a similar name. {COUNTRY_HINT}
adverse_media = ONLY compliance-relevant findings about THIS entity (sanctions, export controls, military or
state links, fraud/corruption, money laundering, enforcement, national-security reviews). Exclude business news,
governance votes, product or HR stories.
events = dated stakeholder actions involving this entity: investments/funding rounds, acquisitions announced or
completed, relocations/re-domiciling, government inquiries, regulator decisions, listings on government lists.
{as_of_txt}
SOURCES:
{chr(10).join(blocks)}

POLICY EXCLUSION RULES:
{policy_txt}

Return JSON:
{{"canonical_name":"", "aliases":[""], "native_names":["e.g. Chinese name if stated"],
 "facts":{{
   "incorporation_country":{{"value":"","quote":"","src":""}},
   "hq_country":{{"value":"","quote":"","src":""}},
   "principal_place_of_business_country":{{"value":"","quote":"","src":""}},
   "majority_team_country":{{"value":"","quote":"","src":""}},
   "founded_in_country_of_concern":{{"value":false,"quote":"","src":""}},
   "hq_address":{{"value":"","quote":"","src":""}},
   "description":{{"value":"one line","quote":"","src":""}}
 }},
 "sectors":[{{"value":"one of: ai, semiconductors, quantum, hypersonics, hpc, biotech, defense, surveillance, fintech, consumer, other","quote":"","src":""}}],
 "owners":[{{"name":"","type":"company|person|fund","country":"","pct":null,"quote":"","src":""}}],
 "subsidiaries":[{{"name":"","country":"","pct":null,"quote":"","src":""}}],
 "investors":[{{"name":"","type":"fund|company|person","country":"","pct":null,"quote":"","src":""}}],
 "key_people":[{{"name":"","role":"","quote":"","src":""}}],
 {kind_specific}
 "events":[{{"date":"YYYY-MM-DD or YYYY-MM","actor":"who acted","action":"what they did, <=15 words","category":"investment|acquisition|relocation|government_inquiry|regulator_decision|listing|other","quote":"","src":""}}],
 "adverse_media":[{{"summary":"","category":"sanctions|export_controls|military_link|state_control|fraud_corruption|money_laundering|enforcement_action|national_security_review","quote":"","src":""}}],
 "policy_hits":[{{"rule_id":"","summary":"","quote":"","src":""}}]
}}"""
        out = llm.complete_json(prompt, model=LLM_SMART_MODEL if node.depth == 0 else None, timeout=240)
        return {"raw": out, "src": src_index}

    # ------------------------------------------------------- verification
    @staticmethod
    def _norm_txt(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").lower()).strip()

    def _verify(self, item: dict, src_index: dict) -> Evidence | None:
        """A claim survives only if its quote is actually present in the cited source."""
        if not isinstance(item, dict):
            return None
        sid, quote = item.get("src"), item.get("quote") or ""
        s = src_index.get(sid)
        if not s or len(quote) < 8:
            return None
        hay, needle = self._norm_txt(s["text"]), self._norm_txt(quote)
        if not (needle in hay or fuzz.partial_ratio(needle, hay) >= 90):
            return None
        return Evidence(s["url"], s["domain"], quote, s["engines"], s["sha256"], s["date"], s["snapshot"])

    # ------------------------------------------------------------ process
    def _process(self, node: Node):
        node.status = "researching"
        self._ev("node", node=node.to_dict())
        self._log(f"Researching {node.name} (depth {node.depth})" + (f" as of {self.as_of}" if self.as_of else ""), node.id)

        hits, platform = self._retrieve(node)
        ranked = self._rank(hits)
        before = self.excluded_sources
        admitted = self._admit(ranked)
        if self.as_of:
            snaps = sum(1 for a in admitted if a["snapshot"])
            self._log(f"Time filter: admitted {len(admitted)} sources dated <= {self.as_of} "
                      f"({snaps} via archived snapshots), excluded {self.excluded_sources - before}", node.id)
        to_read = [a["read_url"] for a in admitted[:8 if node.depth == 0 else 5]]
        pages: dict[str, Page] = {}
        if to_read and not self.meter.exhausted:
            for p in self.sc.read(to_read):
                pages[p.url.rstrip("/")] = p
        pages = {u: pages[u.rstrip("/")] for u in to_read if u.rstrip("/") in pages}
        self._meter()
        if self.as_of:   # layer 3: content scan (catches wrong provider dates)
            kept, leaked = [], 0
            for a in admitted:
                p = pages.get(a["read_url"])
                text = (p.content if p and p.ok else "") + " " + " ".join(h.snippet for h in a["hits"])
                if mentions_future(text, self.as_of):
                    leaked += 1
                    continue
                kept.append(a)
            if leaked:
                self.excluded_sources += leaked
                self._log(f"Content scan: dropped {leaked} source(s) that mention years after {self.as_of} "
                          f"(wrong provider dates)", node.id)
            admitted = kept
        node.sources = [{"url": a["url"], "engines": sorted({h.engine for h in a["hits"]}), "title": a["hits"][0].title,
                         "date": a["date"], "snapshot": a["snapshot"],
                         "read": a["read_url"] in pages and pages[a["read_url"]].ok,
                         "sha256": pages[a["read_url"]].sha256 if a["read_url"] in pages else None}
                        for a in admitted[:10]]
        self._log(f"{len(hits)} results from {len({h.engine for h in hits})} engines -> {len(ranked)} unique URLs, "
                  f"read {sum(1 for p in pages.values() if p.ok)}", node.id)

        try:
            ext = self._extract(node, admitted, pages, platform)
        except llm.LLMError as e:
            self._log(f"extraction failed: {e}", node.id)
            node.status = "done"
            return []
        raw, src = ext["raw"], ext["src"]

        claims_total = claims_ok = 0
        facts: dict = {"aliases": raw.get("aliases") or [], "native_names": raw.get("native_names") or []}
        fact_evidence = {}
        for k, item in (raw.get("facts") or {}).items():
            if not isinstance(item, dict) or item.get("value") in (None, "", False):
                continue
            claims_total += 1
            ev = self._verify(item, src)
            if ev:
                claims_ok += 1
                facts[k] = item["value"]
                fact_evidence[k] = ev.to_dict()
        sectors = []
        for item in raw.get("sectors") or []:
            claims_total += 1
            if self._verify(item, src):
                claims_ok += 1
                sectors.append(item.get("value"))
        facts["sectors"] = sorted({s for s in sectors if s})
        facts["evidence"] = fact_evidence
        facts["country_hint"] = node.facts.get("country_hint")
        node.facts = facts
        if raw.get("canonical_name") and node.depth == 0:
            node.facts["canonical_name"] = raw["canonical_name"]

        children: list[tuple[Node, float]] = []
        holders: list[dict] = []   # equity holders for the outbound-rule ownership test

        def rel(items, edge_type, direction, kind_default, cap=8):
            nonlocal claims_total, claims_ok
            for it in (items or [])[:cap]:
                if not isinstance(it, dict) or not it.get("name") or _generic(it["name"]):
                    continue
                claims_total += 1
                ev = self._verify(it, src)
                if not ev:
                    continue
                claims_ok += 1
                if fuzz.token_sort_ratio(self._key(it["name"]), node.id) >= 92:
                    continue
                # Look-through direction: from the target go both ways; from an owner keep going
                # up (who owns the owner); from a subsidiary/portfolio company keep going down.
                if node.direction == "up" and direction == "out":
                    continue
                if node.direction == "down" and direction == "in" and edge_type != "owns":
                    continue
                kind = it.get("type") if it.get("type") in ("company", "person", "fund") else kind_default
                is_new = self._find(it["name"]) is None
                child = self._add_node(it["name"], kind, node.depth + 1)
                if is_new:
                    child.direction = "up" if direction == "in" else "down"
                if it.get("country") and not child.facts.get("country_hint"):
                    child.facts["country_hint"] = it.get("country")
                pct = it.get("pct") if isinstance(it.get("pct"), (int, float)) else None
                if direction == "in":
                    self._add_edge(child, node, edge_type, pct, [ev], it.get("role", ""))
                    if edge_type in ("owns", "invests"):
                        holders.append({"name": it["name"], "pct": pct, "country": (it.get("country") or "").lower(),
                                        "known_since": ev.date})
                else:
                    self._add_edge(node, child, edge_type, pct, [ev], it.get("role", ""))
                prio = (pct or 0) / 100 + (0.6 if (it.get("country") or "").lower() in CONCERN else 0)
                prio += 0.5 if edge_type in ("owns", "subsidiary", "invests") else 0
                prio += 1.0 if edge_type == "portfolio" else 0
                children.append((child, prio))

        rel(raw.get("owners"), "owns", "in", "company")
        rel(raw.get("subsidiaries"), "subsidiary", "out", "company")
        rel(raw.get("portfolio"), "portfolio", "out", "company")
        rel(raw.get("investors"), "invests", "in", "fund")
        rel([{**p, "type": "person"} for p in raw.get("key_people") or []], "officer", "in", "person", cap=3)

        for e in raw.get("events") or []:
            ev = self._verify(e, src)
            if not ev:
                continue
            d = norm_date(e.get("date"))     # explicit event date only — never the article date
            if not d or (self.as_of and d > self.as_of):
                continue
            self._add_timeline(d, node, "event", e.get("category", "other"),
                               f"{e.get('actor') or node.name}: {e.get('action', '')}", [ev])

        self._screen(node, raw, src, holders)
        node.stats = {"claims": claims_total, "verified": claims_ok,
                      "verify_rate": round(claims_ok / claims_total, 2) if claims_total else None,
                      "engines": sorted({h.engine for h in hits}), "urls": len(ranked), "admitted": len(admitted)}
        node.status = "done"
        self._ev("node", node=node.to_dict())
        self._log(f"{node.name}: {claims_ok}/{claims_total} claims verified against source text; risk={node.risk}", node.id)
        return children

    # ------------------------------------------------------------ timeline
    def _add_timeline(self, d, node: Node, kind: str, category: str, text: str, evidence=None, level: str | None = None):
        key = (d, node.id, text[:60])
        if any((t["date"], t["node"], t["text"][:60]) == key for t in self.timeline):
            return
        item = {"date": d, "node": node.id, "node_name": node.name, "kind": kind, "category": category,
                "text": text, "level": level,
                "evidence": [x.to_dict() if isinstance(x, Evidence) else x for x in (evidence or [])]}
        self.timeline.append(item)
        self._ev("timeline", item=item)

    def _flag(self, node: Node, level: str, kind: str, title: str, detail: str = "", evidence=None,
              extra=None, known_since: str | None = None):
        evs = [e.to_dict() if isinstance(e, Evidence) else e for e in (evidence or [])]
        ks = known_since or _min_date(e.get("date") for e in evs)
        node.flags.append({"level": level, "kind": kind, "title": title, "detail": detail, "evidence": evs,
                           "known_since": ks, **(extra or {})})
        order = {"none": 0, "amber": 1, "red": 2}
        if order[level] > order[node.risk]:
            node.risk = level
        self._add_timeline(ks, node, "signal", kind, title, evs[:1], level)

    def _screen(self, node: Node, raw: dict, src: dict, holders: list[dict]):
        wl = watchlist()
        names = [node.name, *(node.facts.get("aliases") or [])][:4]
        country = (node.facts.get("incorporation_country") or node.facts.get("hq_country")
                   or node.facts.get("country_hint"))
        seen = set()
        for n in names:
            thr = 88 if node.status == "researching" else 93   # stricter when we have no corroborating facts
            for h in wl.screen(n, countries=[country] if country else None, person=(node.kind == "person"),
                               threshold=thr, as_of=self.as_of):
                if h.entity_id in seen:
                    continue
                seen.add(h.entity_id)
                lvl = "red" if h.tier == "binding" and h.score >= 95 else "amber"
                tier_txt = {"binding": "Binding prohibition", "restrictive": "Restrictive / policy list",
                            "other": "Other list"}[h.tier]
                self._flag(node, lvl, "watchlist", f"{h.name} — {tier_txt} ({h.score:.0f}% name match)",
                           f"{h.label}. Listed since {h.listed_since or 'unknown'}.",
                           extra={"match": h.to_dict()}, known_since=h.listed_since)
        node.facts["sanctioned"] = any(
            f["kind"] == "watchlist" and "OFAC SDN" in f.get("match", {}).get("tags", []) for f in node.flags)

        if node.kind == "company" and node.status == "researching":
            o = oisp_assessment(node.facts, holders)
            node.facts["oisp"] = o
            if o["level"] != "none":
                evs = [node.facts["evidence"][k] for k in ("incorporation_country", "hq_country",
                       "principal_place_of_business_country", "majority_team_country", "founded_in_country_of_concern")
                       if k in node.facts.get("evidence", {})]
                self._flag(node, o["level"], "outbound", o["label"], "; ".join(o["signals"]) +
                           (f" | sectors: {', '.join(o['sectors'])}" if o["sectors"] else ""), evs)

        for a in raw.get("adverse_media") or []:
            if not isinstance(a, dict) or a.get("category") in (None, "", "other"):
                continue
            ev = self._verify(a, src)
            if ev:
                serious = a.get("category") in ("sanctions", "export_controls", "military_link")
                self._flag(node, "red" if serious else "amber", "adverse_media",
                           a.get("summary", "Adverse media")[:140], a.get("category", ""), [ev])
        for p in raw.get("policy_hits") or []:
            ev = self._verify(p, src)
            if ev:
                self._flag(node, "amber", "policy", f"Policy: {p.get('rule_id')}", p.get("summary", "")[:200], [ev])

    # --------------------------------------------------------------- run
    def run(self) -> dict:
        self._ev("start", run_id=self.run_id, root=self.root_name, policy_rules=self.policy_rules, as_of=self.as_of)
        root = self._add_node(self.root_name, self.root_kind, 0)
        frontier: list[tuple[Node, float]] = [(root, 9.0)]
        processed = 0
        while frontier and processed < self.max_nodes:
            frontier.sort(key=lambda x: -x[1])
            node, _ = frontier.pop(0)
            if node.status != "queued" or node.depth > self.max_depth:
                continue
            if node.kind == "person":
                continue   # people are screened by name (watchlists/PEP), not researched: follow the money
            if self.meter.exhausted:
                self._log("Budget reached — stopping expansion (remaining nodes screened by name only)")
                break
            kids = self._process(node)
            processed += 1
            frontier += [(c, p) for c, p in kids if c.status == "queued" and c.depth <= self.max_depth]

        for n in self.nodes.values():
            if n.status == "queued":
                self._screen(n, {}, {}, [])
                n.status = "screened"
                self._ev("node", node=n.to_dict())

        blocked = ofac_50({k: n.facts.get("sanctioned", False) for k, n in self.nodes.items()}, self.edges)
        for nid, why in blocked.items():
            n = self.nodes[nid]
            self._flag(n, "red", "ofac50", "Blocked by OFAC 50% rule (aggregate ownership)",
                       f"{why['aggregate_pct']:.0f}% owned by blocked persons: "
                       + ", ".join(self.nodes[v].name for v in why["via"]))
            self._ev("node", node=n.to_dict())

        result = self.snapshot()
        (RUNS_DIR / f"{self.run_id}.json").write_text(json.dumps({**result, "events": self.events}, default=str))
        self._ev("done", result=result)
        return result

    def snapshot(self) -> dict:
        nodes = [n.to_dict() for n in self.nodes.values()]
        st = [n["stats"] for n in nodes if n["stats"].get("claims")]
        tl = sorted(self.timeline, key=lambda t: (t["date"] is None, t["date"] or ""))
        return {"run_id": self.run_id, "root": self.root_name, "policy": self.policy, "as_of": self.as_of,
                "policy_rules": self.policy_rules, "nodes": nodes, "edges": self.edges, "timeline": tl,
                "meter": self.meter.to_dict(), "telem_down": self.sc.telem_down,
                "excluded_sources": self.excluded_sources,
                "verification": {"claims": sum(s["claims"] for s in st), "verified": sum(s["verified"] for s in st)},
                "elapsed_s": round(time.time() - self.started, 1), "run_date": date.today().isoformat()}
