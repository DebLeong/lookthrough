# Claude Code + LookThrough MCP: time-travel search from any agent

**Prompt** (run from the repo root):
```bash
claude -p "Using only the lookthrough tools: as of 2025-12-29, what was publicly known about US government scrutiny of investment in Manus AI, and was its investor Tencent on any US government list at that date? Verify one key quote with verify_quote before citing it." \
  --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools "mcp__lookthrough__time_travel_search,mcp__lookthrough__verify_quote,mcp__lookthrough__screen_entity"
```

**What Claude Code answered (excerpt, 2026-11-14):**

- **2025-05-09:** Semafor reported "the US Treasury Department is reviewing a Benchmark Capital-led $75 million investment in Chinese startup Manus AI."
- **Verified quote:** TechCrunch, 2025-05-09: "the investment is now under review by the U.S. Treasury Department over its compliance with 2023 restrictions on investing in Chinese companies." `verify_quote` found an exact match on the Internet Archive capture from 2025-09-09, before the as-of date.
- **Tencent on a US list:** DoD 1260H, listed since 2025-01-07. Classed as *restrictive*: a Pentagon procurement ban, not an investment ban. No binding listing (OFAC SDN or NS-CMIC) as of that date.
- **Tencent as a Manus investor: not confirmed.** The time-bounded search found no source before 2025-12-29 naming Tencent as a backer, so Claude declined to assert it.

That last bullet is the point. Ordinary agent search would have used today's knowledge, which leaks the future. With LookThrough, the agent states only what it can source and verify *inside the time window*.

---

## Baseline: same question, plain Claude Code web search (no LookThrough)

Same prompt, tools `WebSearch,WebFetch` only, run 2026-11-14. Plain search is *good at finding facts*. It found the Treasury review, Tencent as a backer and the 1260H listing. But:

1. **It leaks the future.** To answer "as of 2025-12-29" it reasoned from later events: *"The next update wasn't until February 2026… The June 2026 update also kept Tencent on the list."* In a lookback or audit, hindsight contaminates the record.
2. **Its quotes aren't machine-verified.** WebFetch returns a model summary of the page; the "verbatim" quote is never checked against page text or an archived snapshot.
3. **It checked one list.** In its own words: "I only checked the 1260H list; I didn't check whether Tencent appeared on other US lists." LookThrough screens about 66k entities across OFAC, 1260H, BIS, UN, UK and EU, with listing dates, every time.
4. **No audit trail.** Re-run it and you may get different sources. LookThrough records sources, dates, hashes and a Telem session.

**Honest gap:** LookThrough's quick `time_travel_search` did not surface Tencent-as-investor for that query. The full look-through agent did (Tencent is an investor node in the as-of run). Recall is something we keep improving, and we never trade it for leakage.

---

## Hindsight test 2: Builder.ai as of 2023-05-01 (run 2026-11-14)

### Plain Claude Code (WebSearch/WebFetch)
```
Up to 2023-05-01, nearly all the public concern about Builder.ai's AI claims came from one cluster of reporting in August 2019. The later stories about faked revenue and the 2025 insolvency came after your cutoff, so they're left out.

- **14 Aug 2019 – Wall Street Journal investigation.** The WSJ ("AI Startup Boom Raises Questions of Exaggerated Tech Savvy") reported that, according to documents and current and former staff, Engineer.ai did not use AI to assemble app code as it claimed. Verbatim quote, as excerpted on Slashdot: **"They indicated that the company relies on human engineers in India and elsewhere to do most of that work."** The WSJ article is paywalled, so I took the quote from Slashdot's excerpt rather than the original. Source: https://news.slashdot.org/story/19/08/14/1345247/ai-startup-boom-raises-questions-of-exaggerated-tech-savvy

- **14 Aug 2019 – The Verge's follow-up (Nick Statt).** It summarised the WSJ findings: the company said it could build most of a mobile app in about an hour and had raised nearly $30M, including from a SoftBank-owned fund. It also reported that the company's "human-assisted" AI seemed limited to basic tools, such as natural language processing for price quotes and a decision tree for assigning tasks. Source: https://www.theverge.com/2019/8/14/20805676/engineer-ai-artificial-intelligence-startup-app-development-outsourcing-humans

- **Feb 2019 (reported Aug 2019) – Former executive's lawsuit.** Former chief business officer Robert Holdheim sued for wrongful termination in Los Angeles. He alleged that founder Sachin Dev Duggal told investors the product was 80% built when development had barely begun. These were allegations, not court findings. I didn't find the docket or how the case ended. Source: https://thenextweb.com/news/this-startups-ai-to-build-your-apps-is-just-a-bunch-of-human-devs (TNW, 15 Aug 2019)

- **Aug 2019 – The company's response.** Duggal disputed the report: "We never said we use AI to assemble code. We said we use a Human-Assisted AI to run the end to end process." Investor Jungle Ventures said the company had always been honest about using human-assisted AI. TNW also reported that Duggal had said startups exaggerate to get funding. Sources: https://inc42.com/buzz/engineer-ai-accused-exaggerating-its-ai-tech and https://analyticsindiamag.com/should-engineer-ai-be-blamed-for-exaggerated-claims/

- **2020 – early 2023 – Rebrand and new funding without new revelations.** Engineer.ai renamed itself Builder.ai. Secondary sources disagree on whether that was 2019 or 2020. It went on to raise large rounds, including a Series D reported in early 2023. In what I found, the 2019 WSJ story was the only major public account questioning its AI claims, and I found no published concerns about its finances before May 2023. This bullet comes from my own recall plus secondary sources, which conflict on dates. Source: https://www.eweek.com/news/builderai-bankruptcy-ai-developers-coding/
```

### Claude Code + LookThrough MCP
```
As of 2023-05-01, the public concerns were about Builder.ai overstating its AI. I found nothing from before that date questioning its revenue or finances. Only the Verge quote below went through verify_quote; the other bullets rely on page excerpts the search tool returned.

- **2019-08-14, WSJ: the original report.** "AI Startup Boom Raises Questions of Exaggerated Tech Savvy" (Newley Purnell and Parmy Olson). It reported that several current and former employees said Engineer.ai "exaggerates its AI capabilities to attract customers and investors." https://www.wsj.com/articles/ai-startup-boom-raises-questions-of-exaggerated-tech-savvy-11565775004

- **2019-08-14, The Verge: humans did the work (verified quote).** The article says "the WSJ reports that Engineer.ai does not use AI to assemble the code, and instead uses human engineers in India and elsewhere to put together the app." verify_quote found an exact match. It checked today's live page, though, because no Internet Archive snapshot came back. https://www.theverge.com/2019/8/14/20805676/engineer-ai-artificial-intelligence-startup-app-development-outsourcing-humans

- **Early 2019, insider lawsuit (reported by the Verge, 2019-08-14).** Chief business officer Robert Holdheim sued the company. He alleged that founder Sachin Dev Duggal "was telling investors that Engineer.ai was 80% done with developing a product that…" was not close to that stage. The Next Web (2019-08-15) quoted Duggal's 2018 claims that "majority of the work is done by AI" and that 82% of one app was built by AI in under an hour. It also cited people who said the company had started building its AI capabilities only in the previous two months. https://thenextweb.com/news/this-startups-ai-to-build-your-apps-is-just-a-bunch-of-human-devs

- **2019–2020, rebrand and continued reporting.** The company renamed itself Builder.ai in October 2019. Business Insider (2020-06-04) repeated the WSJ allegations and noted that a cloud-software resale business "is thought to account for a chunk of its revenue". That was the only public hint about how its revenue was made up. Entrackr (2019-08-17) covered the company's response to the WSJ. https://www.businessinsider.com/engineerai-builderai-layoffs-14-percent-staff-2020-6 · https://entrackr.com/2019/08/engineer-ai-faked-ai-capabilites

- **2022-03-30, big claims and new money despite the concerns.** TechCrunch reported a $100M Series C led by Insight Partners, with the IFC also participating. The company now claimed it could build apps "up to 6x faster and up to 70% cheaper" than human teams. These are the company's own claims and weren't independently checked. https://techcrunch.com/2022/03/30/builder.ai-raises-100m-series-c-led-by-insight-partners-to-scale-up-its-software-automation **Screening:** `screen_entity("Builder.ai", as_of=2023-05-01)` returned no hits on any watchlist. This was always a fraud and misrepresentation risk, not a sanctions one.

**Two sources excluded as date errors:** the tool admitted centerconsulting.com (labelled 2019-08-15) and augment.market (labelled 2022-03-01) as dated before 2023-05-01. Both pages actually describe Builder.ai's 2025 insolvency, so I left them out. This is the "provider publish dates can be wrong" caveat noted in CLAUDE.md, and it shows dated pages can leak through the as-of filter too.
```
