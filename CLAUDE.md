# LookThrough: project notes

**"When a deal blows up, everyone asks: what did you know, and when?"** LookThrough rebuilds what was publicly knowable about any company on any past date, in about 90 seconds:
- **time-bounded:** only sources public then;
- **verified:** every claim has a verbatim quote checked against its source;
- **connected:** investors, owners and subsidiaries mapped live.

Tagline used today: "a dashcam for due diligence". A suggested alternative is "What did you know, and when?", since a dashcam records forward while LookThrough rebuilds the past.

Built at **SearchHack (Telem AI), 2026-11-14**, on Telem's multi-engine search router.

## ⚠️ After the hackathon (2026-11-14), do these
- [ ] **Make the GitHub repo private:**
  `gh repo edit DebLeong/lookthrough --visibility private --accept-visibility-change-consequences`
- [ ] **Retire the public demo.** Stop the tunnel (`pkill cloudflared`) and the public server (port 8078).
- [ ] **Let the laptop sleep:** `pkill caffeinate`.
- [ ] Optional: rotate the Telem and Tavily API keys. They were never committed, but they were used on a public demo.
- [ ] Note: OpenSanctions data is CC BY-NC. Any commercial use needs a license.

## Run it
```bash
.venv/bin/uvicorn app.server:app --port 8077                              # local: unrestricted live runs
LOOKTHROUGH_PUBLIC_LIVE=1 .venv/bin/uvicorn app.server:app --port 8078    # public: guarded live runs
cloudflared tunnel --no-autoupdate --url http://localhost:8078            # public URL (changes on restart, so regenerate the QR)
caffeinate -dims
```
**Server modes:**
- default: unrestricted.
- `LOOKTHROUGH_PUBLIC_LIVE=1`: one live run at a time, at most 6 fresh runs per hour (`LOOKTHROUGH_PUBLIC_MAX_PER_HOUR`), capped at depth 1 / 2 entities / $0.50. Monitors are blocked. Cached runs don't use a slot.
- `LOOKTHROUGH_READONLY=1`: replays only.

**Live updates use polling:** `/api/start` then `/api/events/{key}?since=n`, and replays use `/api/replay_json/{id}`. The Cloudflare quick tunnel buffers Server-Sent Events, so the UI polls every 0.7 s instead. The SSE endpoints (`/api/run`, `/api/replay`) still exist for local use.

**`.env`:** `Telem_API_key` (or `TELEM_API_KEY`), `Tavliy_API_key` (or `TAVILY_API_KEY`). The **hackathon Telem base URL is `https://hack.telem.ai/api`** (keys come from hack.telem.ai; `router.telem.ai` rejects them).

**LLM:** the local `claude` CLI on the user's personal subscription. Do **not** switch to an API key. Calls are throttled (one at a time, at least 3 s apart, at most 12 per minute) and cached (`app/llm.py`). This throttle is the throughput bottleneck: a new company takes about 2–3 minutes.

## URLs
- Local: http://localhost:8077 · `/story` (slides) · `/` (investigation) · `/compare` (hindsight test) · `/pitch` (who it's for)
- Public (this session only): https://reaction-asset-colours-health.trycloudflare.com. QR in `media/qr-demo.png`.
- Repo: https://github.com/DebLeong/lookthrough

## Showcase case: Builder.ai (Manus was dropped as too geopolitical)
- Investigation: `builder-ai-61aba5` (19 entities, 63/65 claims verified). Demo link: `/?replay=builder-ai-61aba5&speed=6`.
- **Public before the 2023 rounds:**
  - Feb 2019: an ex-executive sues, alleging investors were told the product was "80% built";
  - Aug 2019: WSJ, "exaggerates its AI capabilities…";
  - Aug 2019: The Verge, "human engineers in India…" (quote machine-verified);
  - Jun 2020: Business Insider on cloud-resale revenue.
- **What investors did:** Insight Partners led $100M in 2022; Qatar Investment Authority and Microsoft backed it in 2023; insolvency followed in 2025.
- **Hindsight test** (`/compare`, transcript in `docs/claude-code-demo.md`): asked "as of 2023-05-01", plain Claude search brought up the 2025 insolvency, cited a 2025 bankruptcy article, and said "my own recall". LookThrough stayed inside the window and verified its quote. It also caught 2 wrong-dated sources, which led to the new content scan.
- **Backup case: Wirecard/SoftBank** (as-of 2019-04-23 run plus live run, and a plain-search baseline that leaked "June 2020").
- **Other saved companies (instant):** Super Micro Computer (12 flags: Hindenburg, SEC 2020, DOJ probe, auditor resignation), Scale AI, DeepSeek, DJI, ByteDance, MiniMax, Zhipu AI, Unitree Robotics, Moonshot AI, Pony.ai, HongShan, Manus AI. The UI opens a saved company instantly when the name matches (case-insensitive).

## Key numbers (aggregate across 19 investigations; safe to say)
- **151** later sources blocked.
- **97% of 493** claims verified.
- **161** entities mapped.
- **10** engines and platforms.
- The **best single engine found only 64%** of the verified evidence.

**Spend:** about $4 of the $50 Telem credit, plus about 54 of the 8,000 Tavily credits (search is about $0.20 per investigation; caching makes replays free).

**Market:**
- $206B a year on financial-crime compliance, 57% labor (LexisNexis 2023);
- 15,352 US VC deals in 2025, $320B, 65% into AI (NVCA);
- research showing date-filtered retrieval alone leaks the future (*Pitfalls in Evaluating LM Forecasters*; Li et al. 2026).

## Presentation and submission files
- `web/story.html`: 9 numbered slides:
  1. the question;
  2. who it's for;
  3. the Builder.ai story;
  4. the warnings were public;
  5. the pain today;
  6. how it works;
  7. built on Telem (routing 64%, +2 platforms, date filter + trace; **don't claim Telem "searches the web as it was"**);
  8. recap (who, why, how);
  9. try it / QR.
- `VIDEO.md`: 2-minute script. `PRESENTATION.md`: stage run of show and Q&A. `PROJECT_STORY.md`: clean Devpost "About" text. `SUBMISSION.md`: all Devpost fields.
- Images: `media/0-story-hook.png`, `6-story-case.png`, `5-hindsight-test.png`, `1-live-graph.png`, `7-story-market.png`, `4-who-its-for.png`.

## Q&A positions
- **Low spend:** it's efficiency, about 20 cents an investigation.
- **"Can't Claude do this with a good prompt?"** Not reliably: the model knows the ending, its search has no date filter, quotes go unverified, and runs aren't reproducible.
- **Closest competitors:**
  - Sayari (time-stamped ownership records);
  - manual lookbacks by consultancies (FTI, K2);
  - Castellum.AI lookbacks;
  - Orbis Historical / World-Check change history (registry and list data, not open-web evidence);
  - Harvey and Legora (reason over documents you already have; they time-stamp their own work, not past knowability). They're potential partners via MCP.
- Always say **"we found no public product,"** never "nobody does this."
- **Moonshot AI is a Sky9 portfolio company, and a Sky9 partner is judging.** Don't volunteer it.

## Code map
- `app/agent.py`: retrieve (Telem auto-routing, plus a **red-flag sweep** on the target: short-seller, auditor/restatement/SEC, lawsuit/DOJ queries; pinned WeChat/LinkedIn; Tavily) → rank (cross-engine consensus) → admit (as-of: dated ≤ date, or a Wayback snapshot) → read (Telem Fetch, 8 pages for the target, 5 otherwise) → **content scan** (drop sources mentioning years after the as-of date) → extract (Claude, verbatim quotes) → verify → screen → expand. People are screened by name only (follow the money); funds prioritize portfolio links.
- `app/tickers.py`: ticker → company name via Telem search ("SMCI" → Super Micro Computer, "0700.HK" → Tencent).
- `app/rules.py` (outbound rule, OFAC 50%), `app/screening.py` (OpenSanctions fuzzy matching, binding/restrictive tiers, listing dates), `app/search.py` (Telem/Tavily, cache, meter), `app/wayback.py`, `app/mcp_server.py` (MCP tools `time_travel_search`, `verify_quote`, `screen_entity`; `.mcp.json`).
- `app/server.py`: FastAPI routes and the polling API. `web/`: `index.html`, `story.html`, `compare.html`, `pitch.html`.

## Known limits
- Provider publish dates can be wrong (mitigated by the content scan; that scan can also over-exclude pages with forward-looking years).
- Undated evidence doesn't show at past slider dates.
- Private ownership percentages are rarely public.
- New runs take 2–3 minutes.
- Short company names may be treated as tickers.
- No image, video or audio search.
