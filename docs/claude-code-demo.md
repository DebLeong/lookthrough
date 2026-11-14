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
