## Inspiration
**When a deal blows up, everyone asks one question: "What did you know, and when?"** The board asks it. So do the investors, the regulator, the lawyers and the insurer.

I spent years in hedge-fund compliance answering that question by hand. It takes weeks of analysts and lawyers. **AI search makes it worse:** ask it about 2023 and it answers with 2025. It already knows how the story ended.

Take **Builder.ai**, the "AI" app-builder backed by Microsoft and SoftBank. It raised big rounds through 2022–2023 and collapsed into insolvency in 2025, amid reports its revenue was overstated. The first question to its investors was: *didn't you see the warnings?*

## What it does
**LookThrough rebuilds what was publicly knowable about any company, on any past date, in about 90 seconds.** You type a company and pick a date.

- **Time-bounded:** only sources public on that date. Three layers keep later information out: Telem's publish-date filter, Internet Archive snapshots for undated pages, and a content scan that drops any page mentioning a later year. **151 later sources** were blocked across our runs.
- **Verified:** the AI may only propose facts with a verbatim quote, and code checks every quote against the source page. **97% of 493 claims** matched word for word; the rest were dropped.
- **Connected:** an agent maps investors, owners and subsidiaries live from the web. **161 entities** were mapped across 19 investigations.
- **A timeline:** what was public when, next to what decision-makers actually did.

**What was public about Builder.ai before the 2023 rounds:**
- Feb 2019: an ex-executive sued, alleging investors were told the product was "80% built".
- Aug 2019: the WSJ reported it "exaggerates its AI capabilities to attract customers and investors".
- Aug 2019: it "uses human engineers in India… to put together the app" *(quote machine-verified)*.
- Then: Insight Partners led a $100M round in 2022, and more backing followed in 2023.

## The hindsight test
We asked the same AI (Claude Code) the same question: *"What was known about Builder.ai's problems as of May 2023?"*
- **Plain AI search** brought up "the 2025 insolvency", cited a 2025 bankruptcy article as evidence, and admitted one point came "from my own recall".
- **LookThrough** used only sources from before the date, verified its key quote, and caught two sources whose publish dates were wrong.

**Smart AI search knows the ending. In a lookback, being right with hindsight is being wrong.**

## Who it's for
Anyone who signs off on risk:
- **investors** (15,352 US VC deals in 2025, $320B), plus PE and M&A;
- **banks and fintechs** ($206B a year on financial-crime compliance, LexisNexis 2023);
- **insurers, auditors and law firms**, whose claims, audits and lawsuits all turn on "what was known at the time";
- **AI agents** that backtest or recommend decisions. Research shows date-filtered retrieval alone still leaks the future.

**First wedge:** investor due diligence. **Platform:** an API and MCP tool any agent can call. It also includes sanctions and government-list screening (OFAC, DoD 1260H, BIS, UN, UK, EU) with listing dates.

## How we used Telem
- **Auto-routing:** no single search engine sees it all. **The best single engine found only 64% of our verified evidence;** Telem's routing across 10 engines and platforms found the rest.
- **Pinned platforms:** WeChat and LinkedIn add sources ordinary web search misses.
- **`published_before`:** the first layer of time travel.
- **Fetch and sessions:** pages are read with automatic fallback between fetchers, and every search is logged in one Telem session per investigation, which serves as the audit trail.
- **Monitors:** one click re-screens a flagged company every hour.

## How we built it
- **Stack:** Python and FastAPI streaming live updates (Server-Sent Events) to a Cytoscape.js interface, with Claude extracting facts.
- **Pipeline:** retrieve, rank by cross-engine agreement, apply the time filter, read the pages, extract quotes, verify them, screen, then expand the graph.
- **MCP server:** `time_travel_search`, `verify_quote` and `screen_entity` let Claude Code or any agent use time-travel search.
- **Cost:** everything is cached, so replays are free. Total search spend for the whole day was under $5.

## Challenges
- **Time leakage is subtle.** Search providers sometimes return wrong publish dates; two pages labelled 2019 and 2022 were really about 2025. We added a content scan to catch these automatically.
- **No guessing.** When evidence is thin, LookThrough says "not established" instead of inventing an answer.

## What we learned
For high-stakes decisions, the most valuable output of AI search isn't an answer. It's **a reproducible, time-stamped, cited record of what could be known.** Incumbents sell historical data and consultancies run manual lookbacks; we found no product that rebuilds this on demand in minutes.

## What's next
- Pilots with funds, plus connectors to data rooms and registries.
- The same engine for banks (KYC refreshes), insurers (claims), law firms (lookbacks), and AI teams that need backtests free of hindsight.

*Screening signals for review, not legal advice.*
