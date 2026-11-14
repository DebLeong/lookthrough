# LookThrough

**Time-travel search for AI agents.** AI search answers *what's true now*; LookThrough answers *what was knowable then, and how do we know*: retrieval that is **time-bounded** (no future leakage), **verified** (every claim quote-checked against its source) and **connected** (it builds a knowledge graph across engines, languages and archives). We prove it on cross-border investment diligence. LookThrough rebuilds a company's ownership graph and risk picture *as it was knowable on any past date*, using only evidence published before that date, and lines it up against what investors and acquirers actually did.

Built in one day at **SearchHack** (Telem AI) on Telem's multi-engine search router.

> Screening signals for counsel review — not legal advice.

![LookThrough](media/1-live-graph.png)

## Why

US investors now carry legal duties three layers down:

- **US Outbound Investment Rule** (31 CFR 850, in force Jan 2025; COINS Act codified it Dec 2025): VC/PE investments in China AI, semiconductors and quantum require a *"reasonable and diligent inquiry"*. Treasury never said what that inquiry looks like, and it is judged on what you knew, or should have known, **at the time of the deal**.
- **OFAC 50% rule**: any entity 50%+ owned, in aggregate, by blocked persons is itself blocked.
- **LP exclusion policies** (1260H "Chinese military companies", surveillance, weapons) reach through funds into portfolio companies.

Incumbents (Orbis, World-Check, Kharon, Sayari) answer *"what is true today"* for entities already in their databases. A deal team needs *"what could we have known on the decision date, and what did we do about it?"*, often for a seed-stage company that isn't in any database.

## What it does

1. **Look-through graph.** From a target, it walks up through owners and investors and down through subsidiaries and portfolio companies, discovering edges live from the web.
2. **Evidence-grounded claims.** The LLM only *extracts*; every fact must carry a verbatim quote, and the quote is checked against the fetched page. Unverified claims are dropped (typically 96–100% survive).
3. **Deterministic rules decide.** Not "the model said so":
   - outbound-rule country and sector tests, including aggregate PRC ownership with undisclosed stakes;
   - OFAC 50% aggregation;
   - watchlist severity tiers (binding vs. restrictive) with listing dates.
4. **As-of mode.** Search is restricted with Telem `published_before`. Undated pages are admitted only through Internet Archive snapshots captured before the date. Watchlist hits must have been listed by then.
5. **Timeline: knowable vs. acted.** Dated signals (list additions, regulator actions) sit beside dated stakeholder actions (funding rounds, relocations, acquisitions). Drag the slider to a decision date and see what was already public.
6. **Continuous monitoring.** One click turns a flagged entity into an hourly Telem Monitor.

## Case study: Manus AI

| Date | Signal / action |
|---|---|
| 2024-01-31 | IDG Capital added to DoD 1260H list |
| 2025-01-07 | Tencent added to DoD 1260H list |
| 2025-04-25 | Benchmark leads $75M Series B with Tencent, HongShan, ZhenFund |
| 2025-06 | Manus moves HQ and ~40 staff from China to Singapore |
| 2025-11 | Reports of US Treasury outbound-rule review of the investment |
| **2025-12-30** | **Meta announces acquisition** |
| 2026-01-01 | China MOFCOM opens investigation |
| 2026-04-27 | China's foreign-investment security review blocks the deal, orders unwind |

The **as-of 2025-12-29** run (the day before Meta's announcement) already flags:
- Tencent on the 1260H list;
- a covered sector (AI) with PRC shareholders whose stakes are undisclosed, so the 50% aggregate test is undetermined;
- the Treasury review.

All of it was knowable. The risk that actually killed the deal came from the *other* jurisdiction. Back office can surface risk; the front office decides. LookThrough produces the decision record.

## How Telem is used

| Need | Telem feature |
|---|---|
| Multi-engine retrieval | `auto_routing: "accuracy"`: Telem classifies each query (e.g. *companies* → Exa/You/Linkup, *financial_filings* → Exa/Perplexity/Tavily) |
| Point-in-time search | `published_before` on every query in as-of mode; `extended` tier for publish dates |
| Chinese-language evidence | Pinned `socialdatax_wechat` provider (WeChat public accounts) |
| People and teams | Pinned `apify_linkedin` provider |
| Reading sources | Telem Fetch with cross-fetcher fallback; page `sha256` stored as evidence hash |
| Audit trail | One Telem **session** per look-through, traced in the Telem console |
| Ongoing compliance | Telem **Monitors** (hourly, agent-checked) on flagged entities |

Cross-engine consensus ranking means URLs returned by more engines and queries are read first.

## Architecture

```mermaid
flowchart LR
  UI[Web UI<br/>graph · timeline · evidence] -->|SSE| API[FastAPI]
  API --> AG[LookThrough agent]
  AG -->|search · fetch · monitors · sessions| T[Telem router<br/>Exa · You · Linkup · Perplexity · Tavily<br/>WeChat · LinkedIn]
  AG -->|bulk adverse media| TV[Tavily direct]
  AG -->|snapshots before as-of date| WB[Internet Archive CDX]
  AG -->|extract w/ verbatim quotes| LLM[Claude]
  AG --> V[Quote verifier]
  V --> R[Rules engine<br/>outbound rule · OFAC 50% · tiers]
  R --> WL[(OpenSanctions<br/>OFAC · DoD 1260H · BIS · UN · UK · EU)]
  AG --> C[(Disk cache + run store<br/>instant replay)]
```

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/download_lists.sh            # OpenSanctions data (CC BY-NC)
cat > .env <<EOF
TELEM_API_KEY=tlm_...
TELEM_BASE_URL=https://hack.telem.ai/api
TAVILY_API_KEY=tvly-...
EOF
.venv/bin/uvicorn app.server:app --port 8077   # open http://localhost:8077
```

The LLM runs through the local `claude` CLI, throttled (one call at a time, at least 3 s apart, at most 12 per minute) and cached. Set `LOOKTHROUGH_READONLY=1` for a public, replay-only instance.

## Code map

- `app/agent.py`: retrieve → rank → admit (as-of) → read → extract → verify → screen → expand
- `app/rules.py`: outbound-rule assessment, OFAC 50% aggregation
- `app/screening.py`: fuzzy watchlist matching, severity tiers, listing dates
- `app/search.py`: Telem + Tavily clients, cost meter, session tracking
- `app/wayback.py`: point-in-time page snapshots
- `web/index.html`: single-page UI (Cytoscape.js)

## Limits

- Private-company ownership percentages are rarely public. LookThrough reports "aggregate test undetermined" and names the shareholders to ask about, rather than guessing.
- Publish dates come from search providers and can be wrong; undated live pages are excluded from as-of runs.
- OpenSanctions data is CC BY-NC; commercial use needs a license.
