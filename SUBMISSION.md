# Devpost submission: copy and paste

## Project name (60 max)
LookThrough: Time-Travel Search for AI Agents

## Elevator pitch (200 max)
AI search answers what's true now. LookThrough answers what was knowable then: time-bounded, quote-verified search building a knowledge graph across engines, languages and archives. Built on Telem.

## Built with (tags)
telem-ai, mcp, claude-code, tavily, exa, perplexity, linkup, you.com, claude, python, fastapi, javascript, cytoscape.js, server-sent-events, opensanctions, internet-archive, wechat, linkedin, rapidfuzz, cloudflare

## "Try it out" links
- Live demo (replay mode): https://reaction-asset-colours-health.trycloudflare.com
- Code: https://github.com/DebLeong/lookthrough

## Image gallery (upload in this order)
1. media/6-story-case.png: what was public vs. what investors did (Builder.ai)
2. media/5-hindsight-test.png: plain AI search vs LookThrough, same question
3. media/1-live-graph.png: the investigation graph
4. media/7-story-market.png: the market
5. media/4-who-its-for.png: who it's for

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

**The case: Builder.ai.** It was the "AI" app-builder backed by Microsoft, SoftBank's DeepCore and Insight Partners. It raised large rounds through 2022–2023 and collapsed into insolvency in 2025, amid reports its revenue was overstated. The question every investor asked afterwards: **were the red flags public before we wrote the check?**

## Who it's for
**The big picture.** Any decision that must hold up later, and any AI agent that makes one, needs to know what was knowable at the time, and prove it:
- **Financial-crime compliance:** $206B a year globally, 57% of it labor (LexisNexis). A KYC refresh is literally "what changed since the last review."
- **Investment and M&A diligence:** 15,352 US VC deals in 2025 alone, plus PE and corporate M&A.
- **AI agents that backtest or forecast:** research shows date-filtered retrieval alone still leaks the future (*Pitfalls in Evaluating Language Model Forecasters*; Li et al. 2026).
- **Legal and insurance:** "what did they know, and when?"

LookThrough is horizontal search infrastructure (API + MCP). **The wedge** is cross-border deal diligence, where a new US law forces a documented inquiry:

- **Daily user: the deal team at a VC or PE fund.** The term sheet is signed with an AI startup that has any Asia nexus (founders, investors, entities, engineers) and the investment committee meets Thursday. They type the name and get the ownership graph, a cited evidence record, and the questions to put to the founder.
- **Budget holder: the General Counsel or CCO.** They own the legal risk (US outbound rule, OFAC 50% rule, LP exclusion policies) and need a time-stamped "reasonable and diligent inquiry" record for every deal, plus monitoring after closing.
- **Expansion:** secondaries buyers and fund-of-funds (hundreds of inherited portfolio companies per deal), corporate M&A teams, banks lending to funds, and law firms.

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
- A **content scan** then drops any source that mentions a year after the cutoff, which catches wrong provider dates.
- Across our runs, **151 later sources were blocked.**

**2. Verified retrieval (no chatbot-on-top hallucination).**
- The LLM may only *propose* facts with a verbatim quote and a source ID.
- Code checks every quote against the fetched page and drops anything that doesn't match. **97% of 493 extracted claims** matched their source word for word; the rest were dropped.
- Deterministic rules, not the model, make the risk calls.

**3. Connected retrieval (a knowledge graph from scattered sources).**
- An agent plans a look-through: up through owners and investors, down through subsidiaries and portfolio companies.
- It routes each sub-question to the right source: live web through Telem's multi-engine router, WeChat and LinkedIn through pinned providers, structured sanctions databases, and the historical archive.
- It assembles a graph whose every edge has a citation and a date.

**And a new interface for it:** a timeline slider over the knowledge graph. Drag it to any date, and the graph shows only what was public then, next to what stakeholders actually did.

**Efficient by design.** Cross-engine consensus ranking means only the top pages are read in full. 19 investigations covering 161 entities cost **$2.64** in total, and cached investigations replay for $0.

## The result on Builder.ai (what was public before the 2023 rounds)
- **Feb 2019:** a former chief business officer sued, alleging the founder told investors the product was 80% built.
- **Aug 2019:** the WSJ reported the company "exaggerates its AI capabilities to attract customers and investors."
- **Aug 2019:** The Verge: it "uses human engineers in India and elsewhere to put together the app" (**machine-verified quote**).
- **Jun 2020:** Business Insider: cloud resale was "thought to account for a chunk of its revenue."
- **Then:** Insight Partners led a $100M Series C in March 2022, followed by larger 2023 backing.

All of it was public. Back office can surface risk; front office decides. LookThrough produces the decision record.

## How we used Telem (the backbone)
- **Auto-routing (`accuracy`)** on every query: Telem classifies intent (*companies* goes to Exa, You.com and Linkup; *financial_filings* to Exa, Perplexity and Tavily), and the UI shows every routing decision.
- **Routing measurably matters.** Across 19 investigations, **the best single engine found only 64% of the verified evidence**; Telem's routing across 10 engines and platforms found the other 36%.
- **`published_before`:** point-in-time retrieval across every engine with one parameter. Time travel is impossible without it.
- **Pinned platforms:** WeChat (Chinese-language sources) and LinkedIn (people and teams) add evidence that web search engines miss.
- **Telem Fetch** with cross-fetcher fallback and page hashes for the evidence trail.
- **Sessions:** one Telem session per investigation, so the whole inquiry is traceable in Telem's console as an audit trail.
- **Monitors:** one click turns a flagged entity into hourly, agent-checked re-screening.

## Time-travel search for any agent (MCP)
LookThrough's primitives also ship as an **MCP server**, so Claude Code, Cursor or any agent can call them:
- `time_travel_search(query, as_of)`
- `verify_quote(url, quote, as_of)`
- `screen_entity(name, as_of)`

**The hindsight test (real outputs, same model, same question):** *"As of 2023-05-01, what was known about concerns that Builder.ai overstated its AI?"*
- **Plain Claude Code web search** found the 2019 reports, but **brought up the ending** ("the later stories about faked revenue and the 2025 insolvency"), **cited a 2025 bankruptcy article** for pre-2023 facts, and admitted one point came from **"my own recall."**
- **Claude Code + LookThrough** stayed inside the window, **machine-verified** its key quote, and **caught two sources with wrong provider dates** (labelled 2019/2022, actually about 2025). That check is now automated with a content scan.

Smart AI search knows the ending, and that's the problem. In a lookback, being right with hindsight is being wrong.

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
