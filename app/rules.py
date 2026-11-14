"""Deterministic compliance rules applied to evidence the agent extracted.

The LLM only *extracts* facts with verbatim quotes; these rules make the call.
That separation is what makes the output auditable ("rules engine over
verified evidence", not "the model said so").

NOT LEGAL ADVICE — outputs are screening signals for counsel review.
"""
from __future__ import annotations

# --- US Outbound Investment Security Program (31 CFR Part 850) ----------------
# Covered foreign person ~ a "person of a country of concern" engaged in a
# covered activity. Country of concern today: PRC incl. Hong Kong & Macau.
# COINS Act proposed rule (Oct 2026) would add Russia, Iran, North Korea, Cuba,
# Venezuela and further sectors — shown separately as "proposed".
OISP_COUNTRIES = {"cn", "hk", "mo"}
COINS_PROPOSED_COUNTRIES = {"ru", "ir", "kp", "cu", "ve"}
OISP_SECTORS = {"semiconductors", "quantum", "ai"}
COINS_PROPOSED_SECTORS = {"hypersonics", "hpc", "biotech"}


def oisp_assessment(facts: dict, parents: list[dict]) -> dict:
    """facts: extracted, quote-verified fields for one entity."""
    signals = []
    inc = (facts.get("incorporation_country") or "").lower()
    hq = (facts.get("hq_country") or "").lower()
    ppb = (facts.get("principal_place_of_business_country") or "").lower()
    team = (facts.get("majority_team_country") or "").lower()
    countries = OISP_COUNTRIES | COINS_PROPOSED_COUNTRIES

    if inc in countries:
        signals.append(f"incorporated in {inc.upper()}")
    if hq in countries:
        signals.append(f"headquartered in {hq.upper()}")
    if ppb in countries:
        signals.append(f"principal place of business in {ppb.upper()}")
    if team in countries:
        signals.append(f"majority of team located in {team.upper()} (LinkedIn)")
    concern_holders = [p for p in parents if (p.get("country") or "").lower() in countries]
    own = sum(p.get("pct") or 0 for p in concern_holders)
    undisclosed = [p["name"] for p in concern_holders if p.get("pct") is None]
    if own >= 50:
        signals.append(f"{own:.0f}% owned by country-of-concern persons")
    elif undisclosed:
        signals.append(f"country-of-concern shareholders with undisclosed stakes ({', '.join(undisclosed[:5])}) "
                       f"— 50% aggregate ownership test undetermined; request cap table")
    if facts.get("founded_in_country_of_concern"):
        signals.append("founded / previously based in a country of concern")

    sectors = {s.lower() for s in facts.get("sectors", [])}
    cur_sector = sectors & OISP_SECTORS
    prop_sector = sectors & COINS_PROPOSED_SECTORS
    cur_country = any(f" {c.upper()}" in s for s in signals for c in OISP_COUNTRIES) or own >= 50
    prop_country = any(f" {c.upper()}" in s for s in signals for c in COINS_PROPOSED_COUNTRIES)

    agg_unknown = bool(undisclosed) and own < 50

    if cur_country and cur_sector:
        level, label = "red", "Potential covered foreign person (current rule)"
    elif (cur_country or prop_country) and (cur_sector or prop_sector):
        level, label = "amber", "Potential coverage under proposed COINS rule"
    elif cur_sector and agg_unknown:
        level, label = "amber", "Covered sector + PRC shareholders: aggregate ownership test needed"
    elif signals and not sectors:
        level, label = "amber", "Country-of-concern nexus; sector unclear"
    elif signals and (cur_sector or prop_sector):
        level, label = "amber", "Covered sector with indirect nexus — inquire"
    elif cur_sector and facts.get("founded_in_country_of_concern"):
        level, label = "amber", "Relocated entity — historical PRC nexus"
    elif cur_country:
        level, label = "amber", "Country-of-concern person — confirm no covered AI/semis/quantum activity"
    else:
        level, label = "none", "No outbound-rule nexus found in evidence"
    return {"level": level, "label": label, "signals": signals, "sectors": sorted(sectors)}


def ofac_50(node_sanctioned: dict[str, bool], edges: list[dict]) -> dict[str, dict]:
    """OFAC 50% rule: an entity owned 50%+ in aggregate, directly or indirectly,
    by blocked persons is itself blocked. edges: {src (owner), dst, pct}."""
    blocked = {k for k, v in node_sanctioned.items() if v}
    reasons: dict[str, dict] = {}
    changed = True
    while changed:
        changed = False
        owners: dict[str, list[tuple[str, float]]] = {}
        for e in edges:
            if e.get("type") == "owns" and e.get("pct"):
                owners.setdefault(e["dst"], []).append((e["src"], float(e["pct"])))
        for dst, lst in owners.items():
            if dst in blocked:
                continue
            agg = sum(p for s, p in lst if s in blocked)
            if agg >= 50:
                blocked.add(dst)
                reasons[dst] = {"aggregate_pct": agg, "via": [s for s, _ in lst if s in blocked]}
                changed = True
    return reasons
