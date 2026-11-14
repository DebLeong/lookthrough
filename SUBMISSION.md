# Devpost submission: copy and paste

## Project name (60 max)
LookThrough: Time-Travel Search for AI Agents

## Elevator pitch (200 max)
AI search answers what's true now. LookThrough answers what was knowable then: time-bounded, quote-verified search building a knowledge graph across engines, languages and archives. Built on Telem.

## Built with (tags)
telem-ai, tavily, exa, perplexity, linkup, you.com, claude, python, fastapi, javascript, cytoscape.js, server-sent-events, opensanctions, internet-archive, wechat, linkedin, rapidfuzz, cloudflare

## "Try it out" links
- Live demo (replay mode): https://reaction-asset-colours-health.trycloudflare.com
- Code: https://github.com/DebLeong/lookthrough

## Image gallery (upload in this order)
1. media/3-asof-run.png: time-travel search to 2025-12-29
2. media/1-live-graph.png: the same investigation, known today
3. media/2-decision-date.png: timeline slider at the decision date
4. media/4-who-its-for.png: who it's for and market size

## Video demo link
(YouTube unlisted URL; see PRESENTATION.md)

---

## About the project (paste everything below)

## Inspiration
AI search is built to answer one question: **what's true now?** Every serious decision asks two harder ones: **what was knowable at the time, and how do we know?**

Today's AI search can't answer them:
- It **leaks the future**: a page fetched today is today's page, and the model reads every update since the date you care about.
- It **hallucinates connections**: a chatbot on top of search will confidently invent who owns whom.
- It **fragments context**: the ownership chain behind one company is scattered across filings, press, LinkedIn, Chinese-language WeChat articles and sanctions lists, and no single engine sees it all.

I spent years in hedge-fund compliance, where getting this wrong is a legal liability. Since 2025, the US Outbound Investment Rule requires a *"reasonable and diligent inquiry"* before backing Chinese AI companies, judged on what you knew **at the time of the deal**. So we built search for that standard, and tested it on a real case.

**The case: Manus AI.** It was founded in China, moved to Singapore in 2025, and Meta announced an acquisition in December 2025. Beijing blocked the deal four months later. Meta had every resource to check. The question isn't *could they know?* It's what was knowable, when, and who went ahead anyway.

## Who it's for
- **Daily user: the deal team at a VC or PE fund.** The term sheet is signed with an AI startup that has any Asia nexus (founders, investors, entities, engineers) and the investment committee meets Thursday. They type the name and get the ownership graph, a cited evidence record, and the questions to put to the founder.
- **Budget holder: the General Counsel or CCO.** They own the legal risk (US outbound rule, OFAC 50% rule, LP exclusion policies) and need a time-stamped "reasonable and diligent inquiry" record for every deal, plus monitoring after closing.
- **Expansion:** secondaries buyers and fund-of-funds (hundreds of inherited portfolio companies per deal), corporate M&A teams (Meta–Manus), banks lending to funds, and law firms.

**Market (bottom-up).**
- In 2025 there were **15,352 US VC deals worth $320B**, and **65% of the dollars went to AI**, the sector the rule covers.
- There are **2,984 US venture firms**. At a $25K/yr subscription (a pricing hypothesis), that's a **~$75M ARR beachhead**, before PE, secondaries, corporate M&A and banks.
- The adjacent "what's true today" risk-intelligence market already supports Quantexa ($2.6B valuation) and Sayari ($235M Series D).

Sources: NVCA 2026 Yearbook; citybiz/NVCA on the AI share.

**Why now.** The COINS Act codified and expanded the rule in December 2025. Its final rule is due in March 2027, and signed-but-unclosed deals aren't grandfathered.

## What it does: three search primitives
**1. Time-bounded retrieval (no future leakage).**
- Every query carries an as-of date, sent to every engine through Telem's `published_before`.
- Undated pages are admitted only through Internet Archive snapshots captured before that date, and watchlist hits must have been listed by then.
- Example: in our Manus run as of 2025-12-29, **54 sources published after the cutoff were excluded.**

**2. Verified retrieval (no chatbot-on-top hallucination).**
- The LLM may only *propose* facts with a verbatim quote and a source ID.
- Code checks every quote against the fetched page and drops anything that doesn't match. **100% of surviving claims are verifiable** (122/122 across both runs).
- Deterministic rules, not the model, make the risk calls.

**3. Connected retrieval (a knowledge graph from scattered sources).**
- An agent plans a look-through: up through owners and investors, down through subsidiaries and portfolio companies.
- It routes each sub-question to the right source: live web through Telem's multi-engine router, WeChat and LinkedIn through pinned providers, structured sanctions databases, and the historical archive.
- It assembles a graph whose every edge has a citation and a date.

**And a new interface for it:** a timeline slider over the knowledge graph. Drag it to any date, and the graph shows only what was public then, next to what stakeholders actually did.

**Efficient by design.** Cross-engine consensus ranking means we read only **18–26% of the URLs found** in full. A 5-entity investigation costs **about $0.25**, and cached investigations replay for $0.

## The result on Manus (as of 2025-12-29, the day before Meta's announcement)
Using only evidence available that day, LookThrough flags:
- **Tencent**, a shareholder, on the Pentagon's 1260H list since January 2025. We label it honestly as a procurement ban, not an investment ban.
- **A reported US Treasury review** of the Benchmark-led round.
- **An AI company whose PRC shareholders have undisclosed stakes**, so the 50% ownership test needs a cap table.
- **The House CCP Committee's 2023 probe** of investor Sequoia China.

All of it was public before the deal. Back office can surface risk; front office decides. LookThrough produces the decision record.

## How we used Telem (the backbone)
- **Auto-routing (`accuracy`)** on every query: Telem classifies intent (*companies* goes to Exa, You.com and Linkup; *financial_filings* to Exa, Perplexity and Tavily), and the UI shows every routing decision.
- **Routing measurably matters.** In the time-travel run, **the best single engine found only 38% of the verified evidence**; Telem's routing found the rest. That's 74% in the live run. Historical evidence is the most scattered, which is where routing pays off most.
- **`published_before`:** point-in-time retrieval across every engine with one parameter. Time travel is impossible without it.
- **Pinned platforms:** WeChat surfaced Chinese-language reporting that Boyu Capital and IDG co-led Manus's latest round, which English search missed. LinkedIn covers team locations.
- **Telem Fetch** with cross-fetcher fallback and page hashes for the evidence trail.
- **Sessions:** one Telem session per investigation, so the whole inquiry is traceable in Telem's console as an audit trail.
- **Monitors:** one click turns a flagged entity into hourly, agent-checked re-screening.

## How we built it
Python and FastAPI stream agent events over Server-Sent Events to a Cytoscape.js UI. The pipeline is:
1. plan;
2. retrieve (Telem plus Tavily);
3. rank by cross-engine consensus;
4. admit (time filter or archived snapshot);
5. read (Telem Fetch);
6. extract (Claude);
7. verify quotes;
8. screen (OpenSanctions: OFAC, DoD 1260H, BIS, UN, UK, EU) and apply rules;
9. expand the graph.

Every external call is cached.

## Challenges
- **Time leakage** is subtle: dates from search providers can be missing or wrong, so undated live pages are excluded from as-of runs rather than trusted.
- **Severity honesty:** our first version treated a 1260H listing as a sanction. It isn't, so we rebuilt the tiers with listing dates.
- **Private ownership is opaque:** instead of guessing percentages, LookThrough says "undetermined" and names the shareholders to ask about.

## What we learned
The most valuable output of AI search for high-stakes decisions isn't an answer. It's a **reproducible, time-stamped, cited record of what could be known**. Incumbents sell historical data pieces, and consultancies run manual lookbacks. We found no product that rebuilds a multi-source picture strictly as it was knowable on a past date.

## What's next
Time-travel search generalizes beyond compliance:
- **litigation and discovery**: what did they know, and when;
- **investigative journalism**;
- **M&A post-mortems**;
- **leak-free backtests and evaluations for forecasting agents**: give an agent only what was knowable at T and score its predictions.

Next steps:
- cap-table ingestion;
- registry and PitchBook connectors;
- pilots with cross-border VC funds, secondaries buyers and fund-of-funds ahead of the COINS final rule (March 2027).

*Screening signals for counsel review, not legal advice. Watchlist data: OpenSanctions (CC BY-NC).*
