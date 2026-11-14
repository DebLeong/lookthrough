"""Watchlist screening against OpenSanctions consolidated sanctions data.

Fuzzy name matching (RapidFuzz) with normalization of legal suffixes and
punctuation, plus a country-agreement boost. Returns candidate hits with the
source lists so the agent can explain *which* list matched and why.

Data: OpenSanctions (CC BY-NC 4.0 — fine for non-commercial/hackathon use;
commercial use requires a license).
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz, process

from .config import LISTS_DIR

ENTITY_SCHEMAS = {"Organization", "Company", "LegalEntity", "Person"}

# Lists that matter most for US investors in China-linked deals get a tag.
PRIORITY_LISTS = {
    "US OFAC Specially Designated Nationals (SDN) List": "OFAC SDN",
    "US OFAC Consolidated (non-SDN) List": "OFAC non-SDN",
    "US DoD Chinese military companies": "DoD 1260H",
    "US Trade Consolidated Screening List (CSL)": "US CSL (BIS Entity List etc.)",
    "US UFLPA Entity List": "UFLPA",
    "UN Security Council Consolidated Sanctions": "UN SC",
    "UK FCDO Sanctions List": "UK",
    "EU Financial Sanctions Files (FSF)": "EU",
}

_SUFFIXES = r"\b(co|company|corp|corporation|inc|incorporated|ltd|limited|llc|plc|gmbh|ag|sa|bv|nv|pte|pty|group|holdings?|technology|technologies|tech|international|intl|the|of|and|jsc|ojsc|pjsc|ooo|zao|kk|srl|spa)\b"


def normalize(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode() or name
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(_SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Severity tiers. "binding" = legal prohibition for US persons (blocking / investment ban);
# "restrictive" = export controls, procurement bans, policy/reputational lists — inquire, not blocked.
BINDING_PROGRAM_PREFIXES = ("US-NS-CMIC",)   # EO 14032: ban on buying publicly traded securities
BINDING_DATASETS = {"US OFAC Specially Designated Nationals (SDN) List", "UN Security Council Consolidated Sanctions"}
PROGRAM_LABELS = {
    "US-DOD-1260H": "DoD 1260H Chinese military company (procurement ban; not an investment ban)",
    "US-NS-CMIC": "NS-CMIC (EO 14032): US persons barred from buying its public securities",
    "US-BIS-EL": "BIS Entity List (export controls)",
    "US-UFLPA": "UFLPA Entity List (import ban)",
}
_DATE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")


@dataclass
class ListHit:
    entity_id: str
    name: str
    matched_alias: str
    schema: str
    score: float
    countries: list[str]
    lists: list[str]
    tags: list[str]
    programs: str
    program_ids: list[str]
    listed_since: str | None      # earliest listing date found in the record (YYYY-MM-DD)
    tier: str                     # binding | restrictive | other

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @property
    def label(self) -> str:
        labs = [PROGRAM_LABELS[p] for p in self.program_ids if p in PROGRAM_LABELS]
        return "; ".join(labs) or ", ".join(self.tags or self.lists[:3])


def _tier(lists: list[str], programs: list[str]) -> str:
    if set(lists) & BINDING_DATASETS or any(p.startswith(BINDING_PROGRAM_PREFIXES) for p in programs):
        return "binding"
    if lists and any(d in PRIORITY_LISTS for d in lists):
        return "restrictive"
    return "other"


def _listed_since(r: dict) -> str | None:
    dates = [m.group(0) for m in _DATE.finditer(r.get("sanctions") or "")]
    return min(dates) if dates else (r.get("first_seen") or "")[:10] or None


class Watchlist:
    def __init__(self, path=LISTS_DIR / "sanctions.csv"):
        self.rows: list[dict] = []
        self.keys: list[str] = []       # normalized names (one per alias)
        self.key_row: list[int] = []
        self.key_raw: list[str] = []
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                if r["schema"] not in ENTITY_SCHEMAS:
                    continue
                idx = len(self.rows)
                self.rows.append(r)
                names = {r["name"], *[a for a in r["aliases"].split(";") if a]}
                for n in names:
                    k = normalize(n)
                    if len(k) >= 3:
                        self.keys.append(k)
                        self.key_row.append(idx)
                        self.key_raw.append(n)

    def screen(self, name: str, *, countries: list[str] | None = None, person: bool | None = None,
               threshold: float = 88, limit: int = 5, as_of: str | None = None) -> list[ListHit]:
        q = normalize(name)
        if len(q) < 3:
            return []
        cands = process.extract(q, self.keys, scorer=fuzz.token_sort_ratio, limit=40, score_cutoff=threshold - 8)
        best: dict[int, ListHit] = {}
        cset = {c.lower() for c in (countries or [])}
        for key, score, ki in cands:
            r = self.rows[self.key_row[ki]]
            if person is not None and (r["schema"] == "Person") != person:
                continue
            # Short names need near-exact agreement to avoid noise ("Manus" vs "Manas").
            if len(q) <= 8 and score < 97:
                continue
            rc = [c for c in r["countries"].split(";") if c]
            adj = score + (4 if cset and cset & set(rc) else 0) - (6 if cset and rc and not cset & set(rc) else 0)
            if adj < threshold:
                continue
            lists = [d for d in r["dataset"].split(";") if d]
            progs = [p for p in r["program_ids"].split(";") if p]
            since = _listed_since(r)
            if as_of and since and since > as_of:
                continue          # not yet listed at the as-of date
            hit = ListHit(r["id"], r["name"], self.key_raw[ki], r["schema"], round(min(adj, 100), 1), rc, lists,
                          sorted({PRIORITY_LISTS[d] for d in lists if d in PRIORITY_LISTS}), r["sanctions"][:300],
                          progs, since, _tier(lists, progs))
            i = self.key_row[ki]
            if i not in best or best[i].score < hit.score:
                best[i] = hit
        return sorted(best.values(), key=lambda h: -h.score)[:limit]


@lru_cache(maxsize=1)
def watchlist() -> Watchlist:
    return Watchlist()
