# LookThrough: project notes

Time-travel search for AI agents, built at **SearchHack (Telem AI), 2026-11-14**. It rebuilds a company's ownership graph and risk picture *as it was knowable on any past date*. Every claim is quote-verified, and the look-through runs across engines, languages and archives. The proof case is cross-border investment diligence (Manus AI / Meta).

## ⚠️ After the hackathon (2026-11-14), do these
- [ ] **Make the GitHub repo private:**
  `gh repo edit DebLeong/lookthrough --visibility private --accept-visibility-change-consequences`
- [ ] **Retire the public demo link.** Stop the Cloudflare tunnel (`pkill cloudflared`) and the public server on port 8078.
- [ ] **Let the laptop sleep again:** `pkill caffeinate`.
- [ ] Optional: rotate the Telem and Tavily API keys in their consoles. They were never committed, but they were used on a shared demo.
- [ ] Note: OpenSanctions data is CC BY-NC. Any commercial use needs a license.

## Run it
```bash
.venv/bin/uvicorn app.server:app --port 8077                                    # local, full live runs
LOOKTHROUGH_PUBLIC_LIVE=1 .venv/bin/uvicorn app.server:app --port 8078          # public, guarded live
cloudflared tunnel --no-autoupdate --url http://localhost:8078                  # public URL (changes on restart)
caffeinate -dims                                                                # keep the Mac awake
```

**Server modes (env vars):**
- default: unrestricted live runs (localhost).
- `LOOKTHROUGH_PUBLIC_LIVE=1`: one live run at a time, at most 6 fresh runs per hour (`LOOKTHROUGH_PUBLIC_MAX_PER_HOUR`), each capped at depth 1 / 2 entities / $0.50. Monitors are blocked. Cached runs don't use a slot.
- `LOOKTHROUGH_READONLY=1`: replays only, no live runs.

**`.env` keys:** `Telem_API_key` (or `TELEM_API_KEY`) and `Tavliy_API_key` (or `TAVILY_API_KEY`). The **hackathon Telem base URL is `https://hack.telem.ai/api`**, and keys come from hack.telem.ai. The main `router.telem.ai` rejects them.

**LLM:** the local `claude` CLI on the user's personal Claude subscription. Do **not** switch to an API key (user's decision). Calls are throttled: one at a time, at least 3 s apart, at most 12 per minute, all cached (`app/llm.py`).

## URLs
- Local: http://localhost:8077 · `/story` (presentation slides) · `/` (investigation) · `/compare` (hindsight test) · `/pitch` (who it's for)
- Public (this session only): https://reaction-asset-colours-health.trycloudflare.com. QR code in `media/qr-demo.png`. **A tunnel restart changes the URL, so regenerate the QR code.**
- Repo: https://github.com/DebLeong/lookthrough

## Saved runs (instant replay; type the name and click Run with the default settings)
- **Manus AI (known today):** `manus-ai-bc261a`. **Manus AI as of 2025-12-29:** `manus-ai-asof-2025-12-29-70460b`. Both were run at depth 2 with 5 entities and the long policy text.
- **Pre-cached at default settings** (depth 1, 2 entities, policy "US investor. Flag outbound-investment exposure and sanctions."): Moonshot AI, DeepSeek, Zhipu AI, MiniMax, Unitree Robotics, DJI, ByteDance, Pony.ai, plus Telem AI as of 2026-06-01, which returned no verifiable facts.
- A fresh live run takes about 45 s to the first result and about 85 s to finish, at about $0.11–0.16.

## Presentation (3 min; script in PRESENTATION.md)
1. **`/story`** (arrow keys), readable on a small screen. Slides: the question, the case, a **before vs. after side by side**, "the risk was public", the hindsight test, the three primitives (54 · 100% · 8), Telem (38%), who pays, and the QR code.
2. Optional cut to `/` for about 20 s: graph, then drag the timeline slider.
3. **Live audience company:** use the two-tab trick, or offer it at the judging table (5:30–6:30). Ask for "any AI or tech company with ties to Asia".
4. **Moonshot AI is a Sky9 portfolio company, and a Sky9 partner (Ara Kyi) is judging.** Don't volunteer it.

## Key numbers (from our runs; safe to say)
- Time-travel run: **54** later sources excluded · **40/40** claims verified · **8** engines · the best single engine found only **38%** of the verified evidence (74% in the live run).
- About $0.25 of search per 5-entity investigation; total saved-run spend about $1.5 of the $50 Telem credit.
- Hindsight test: plain Claude Code answered "as of Dec 2025" using **Feb and June 2026** news (2 leaks), checked 1 watchlist, and verified no quotes. Transcript in `docs/claude-code-demo.md`.

**Market** (sources: NVCA 2026 Yearbook; citybiz/NVCA):
- 15,352 US VC deals in 2025, worth $320B, 65% of the dollars into AI;
- 2,984 US VC firms;
- a $25K/yr subscription gives a ~$75M beachhead. **The price is a hypothesis.**

**Verify before saying on stage:** COINS Act dates (final rule due Mar 2027), and the 1260H procurement-ban dates (FY2024 NDAA Sec. 805).

## Domain facts the product encodes (`app/rules.py`, `app/screening.py`)
- **DoD 1260H** = Pentagon procurement ban, **not** an investment ban, so it's tiered "restrictive" (amber). Binding (red) = OFAC SDN, UN, NS-CMIC (public securities).
- **Outbound rule:** country of concern = PRC, Hong Kong, Macau (COINS proposes adding RU, IR, KP, CU, VE). Covered sectors = AI, semiconductors, quantum (proposed: hypersonics, HPC, biotech). A 50% aggregate PRC ownership test applies; when stakes are undisclosed, say "undetermined, request cap table".
- **OFAC 50% rule:** aggregate ownership by blocked persons.
- Listing dates are parsed from the OpenSanctions `sanctions` field. As-of screening drops listings made after the date.

## Code map
- `app/agent.py`: retrieve → rank (cross-engine consensus) → admit (as-of: dated ≤ date, or a Wayback snapshot) → read (Telem Fetch) → extract (Claude, verbatim quotes) → verify quotes → screen → expand. Look-through direction: from the target go up and down; from owners go up only; from subsidiaries go down only.
- `app/search.py`: Telem (auto-routing, `published_before`, pinned `socialdatax_wechat` / `apify_linkedin`, fetch, sessions) plus Tavily direct. Disk cache and cost meter. Falls back to Tavily if Telem auth fails.
- `app/mcp_server.py`: MCP tools `time_travel_search`, `verify_quote`, `screen_entity`. `.mcp.json` is included.
- `app/server.py`: FastAPI and SSE; routes `/`, `/story`, `/compare`, `/pitch`, `/api/*`, `/media`.
- `web/`: `index.html` (Cytoscape investigation UI), `story.html`, `compare.html`, `pitch.html`.
- Data: `data/runs/*.json` (committed demo runs), `data/cache/` (ignored), `data/lists/sanctions.csv` (download with `scripts/download_lists.sh`).

## Known limits / honest caveats
- Private-company ownership percentages are rarely public.
- Provider publish dates can be wrong; undated live pages are excluded from as-of runs.
- Quick `time_travel_search` recall is lower than the full agent's. For example, it missed Tencent as a Manus investor, which the full agent found.
- No image, video or audio search.

## Submission
Devpost copy is in `SUBMISSION.md` (name, 197-character pitch, about, built-with, links, images `media/1–5`). The video must be recorded by the user (Cmd+Shift+5, uploaded to YouTube as unlisted).
