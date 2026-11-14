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
