# Devpost submission: copy and paste

## Project name (60 max)
LookThrough: Time-Travel Due Diligence

## Elevator pitch (200 max)
See who really stands behind a deal, and what was knowable on any past date. Quote-verified look-through for cross-border investing, powered by Telem multi-engine search.

## Built with (tags)
telem-ai, tavily, exa, perplexity, linkup, you.com, claude, python, fastapi, javascript, cytoscape.js, server-sent-events, opensanctions, internet-archive, wechat, linkedin, rapidfuzz, cloudflare

## "Try it out" links
- Live demo (replay mode): https://reaction-asset-colours-health.trycloudflare.com
- Code: https://github.com/DebLeong/lookthrough

## Image gallery (upload in this order)
1. media/1-live-graph.png: the Manus AI ownership graph, known today
2. media/3-asof-run.png: time-travel to 2025-12-29, the day before Meta announced
3. media/2-decision-date.png: timeline slider set to the decision date

## Video demo link
(YouTube unlisted URL; see PRESENTATION.md for the 90-second recording script)

---

## About the project (paste everything below)

## Inspiration
I spent years in hedge-fund operations and compliance. The hardest question was never "is this name on a sanctions list?" It was **"who is really behind this deal, three layers down, and what did we know when we said yes?"**

That question just became a legal one. The US Outbound Investment Rule (in force January 2025, codified by the COINS Act in December 2025) requires a *"reasonable and diligent inquiry"* before US investors back Chinese AI, semiconductor or quantum companies. Treasury never defined what that inquiry looks like, and it is judged on what you knew, or should have known, **at the time of the deal**.

Then came Manus AI. It was founded in China and moved to Singapore in 2025. Meta announced an acquisition in December 2025, and Chinese regulators blocked the deal in April 2026. Meta had every resource to run checks. The question was never "could they know?" It was **what was knowable, when, and who decided to go ahead anyway.** Back office surfaces risk; front office makes the call. Nobody produces the decision record.

## What it does
LookThrough rebuilds a company's ownership graph and risk picture **as it was knowable on any past date**.

- **Look-through graph:** from a target, it walks up through owners and investors and down through subsidiaries and portfolio companies, discovering every link live from the web.
- **Every claim is quote-verified:** the LLM only extracts facts with a verbatim quote, and we check that quote against the fetched page. Unverified claims are dropped. 96–100% of claims survive on our case runs.
- **Rules decide, not the model:**
  - outbound-rule country and sector tests, including the 50% aggregate ownership test when PRC shareholders' stakes are undisclosed;
  - OFAC 50% aggregation;
  - watchlist severity tiers (a DoD 1260H listing is a procurement ban, *not* an investment ban) with listing dates.
- **Time-travel mode:** every search is restricted to sources published before the chosen date. Undated pages are only admitted through Internet Archive snapshots captured before that date, and watchlist hits must have been listed by then.
- **"Knowable vs. acted" timeline:** dated risk signals sit beside dated stakeholder actions. Drag the slider to the decision date and see exactly what was already public.
- **Continuous monitoring:** one click turns a flagged entity into an hourly Telem Monitor.

**Manus AI, as of 2025-12-29 (the day before Meta's announcement).** LookThrough already flags:
- Tencent, an investor, on the DoD 1260H list since January 2025;
- an AI company with PRC shareholders whose stakes are undisclosed, so the aggregate ownership test needs a cap table;
- a reported US Treasury review of the Benchmark-led round;
- the House CCP Committee's 2023 probe of Sequoia China (HongShan), another investor.

All of it was public before the deal.

## How we used Telem (the core of the build)
- **Auto-routing (`accuracy`)** on every query. Telem classifies the question (*companies* goes to Exa, You.com and Linkup; *financial_filings* to Exa, Perplexity and Tavily) and we surface each routing decision in the UI.
- **Multi-engine evidence matters.** In our time-travel run, the **best single engine found only 38% of the verified evidence**; Telem's routing found the rest. In the live run, the best single engine reached 74%.
- **`published_before`** powers time-travel: point-in-time retrieval across every engine with one parameter.
- **Pinned platform providers:** WeChat (`socialdatax_wechat`) surfaced Chinese-language reporting that Boyu Capital and IDG Capital co-led Manus's latest round; LinkedIn (`apify_linkedin`) covers team location.
- **Telem Fetch** reads sources with cross-fetcher fallback and gives us a page hash for the evidence trail.
- **Sessions:** one Telem session per look-through, so the entire inquiry is traceable in Telem's console. That is the audit trail a "reasonable and diligent inquiry" needs.
- **Monitors:** hourly, agent-checked re-screening of flagged entities.

Without Telem we would need contracts with eight or more search and scraping vendors, plus our own WeChat and LinkedIn access, routing logic and scheduling.

## How we built it
Python and FastAPI stream agent events over Server-Sent Events to a single-page Cytoscape.js UI. The pipeline is: retrieve (Telem plus Tavily), rank by cross-engine consensus, admit (time filter or Wayback snapshot), read (Telem Fetch), extract (Claude), verify quotes, screen (OpenSanctions consolidated lists: OFAC, DoD 1260H, BIS Entity List, UN, UK, EU), apply rules, then expand. Every external call is cached, so finished runs replay instantly and cost nothing.

## Challenges
- **Hallucination in a compliance product is unacceptable.** We solved it structurally: the model only proposes quotes; code verifies them and deterministic rules make the call.
- **Time leakage.** A page fetched today is today's page. As-of mode therefore only admits dated sources from before the cutoff, or archived snapshots captured before it.
- **Severity honesty.** Our first version flagged DoD 1260H matches as red. A 1260H listing is a Pentagon procurement ban, not an investment ban, so we rebuilt the tiers with listing dates.
- **Private ownership is opaque.** Instead of guessing percentages, LookThrough says "aggregate test undetermined" and names the shareholders to ask about.

## What we learned
The valuable output isn't a red flag; it's the **decision record**. Incumbents (Orbis, World-Check, Sayari, Kharon) sell historical data pieces, and consultancies run manual lookbacks. We found no product that rebuilds a company's multi-regime risk picture strictly as it was knowable on a past date and sets it against what decision-makers actually did.

## What's next
- Cap-table ingestion from data rooms for the 50% ownership test.
- PitchBook and registry connectors.
- Investor-side KYC (PEPs, source of wealth) on the same graph.
- Pilots with secondaries buyers, fund-of-funds and cross-border VC funds ahead of the COINS final rule (due March 2027).

*Screening signals for counsel review, not legal advice. Watchlist data: OpenSanctions (CC BY-NC).*
