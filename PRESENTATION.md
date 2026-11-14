# LookThrough: 3-minute final presentation

**Setup before you go on:**
- Open http://localhost:8077 full-screen in Chrome, zoomed to 90%. Use the local server, not the tunnel, in case the venue wifi fails.
- In tab 2, type **Builder.ai** and click Run once (it replays from cache in about 2 s).
- Show the QR code on a phone or a slide: `media/qr-demo.png`. It points to the public replay link.

**Roles:** one person speaks while the other drives the mouse. Rehearse the clicks twice.

---

## The 3-minute run of show: drive `/story` with the arrow keys (one person talks, one clicks)

| Time | Slide | Say |
|---|---|---|
| 0:00 | 1 | "AI search knows what's true *now*. Every deal, audit, claim, lawsuit and AI backtest is judged on what was knowable *then*. LookThrough answers that, with proof. Built on Telem." |
| 0:20 | 2 | "Builder.ai: the AI app-builder backed by Microsoft and SoftBank. Big rounds, then insolvency in 2025. Were the red flags public before the checks were written?" |
| 0:35 | 3 | "Left: what was public before the 2023 rounds. A 2019 lawsuit. The WSJ said it 'exaggerates its AI capabilities.' Humans in India were building the apps; we machine-verified that quote. Right: what investors did anyway." |
| 1:00 | 4 | "The risk was public. Back office surfaces it; front office decides. We produce the defensible record." |
| 1:10 | 5 | "Can't ChatGPT or Claude do this? Plain Claude search brought up the 2025 insolvency and admitted it used its own memory. Smart AI search knows the ending." |
| 1:35 | 6 | "Three primitives: time-bounded, verified, connected." *(optional: press **L** and show the live graph for 15 s)* |
| 1:55 | 7 | "Telem: the best single engine found only 64% of our evidence; routing found the rest. `published_before` makes time travel possible." |
| 2:15 | 8 | "The market: $206B a year in financial-crime compliance, every investment and M&A deal, every AI agent that backtests. Wedge: investor due diligence. Platform: API and MCP." |
| 2:40 | 9 | "I did this by hand for years in hedge-fund compliance. Name a company and we'll show you what was knowable." |

## Optional: live audience company (taking the risk)
Timing measured on Moonshot AI: **first result about 45 s, finished in about 85 s**, $0.11, 2 entities at depth 1 (the app's default settings).

**On stage, two-tab trick:**
1. Before you start, open two tabs at http://localhost:8077.
2. At 0:15, ask: *"Shout out any AI or tech company with ties to Asia."* The driver types it in **tab 2** and clicks **Run**.
3. Do the normal demo in **tab 1**, using the replays.
4. At about 2:30, switch to tab 2: *"…and here's the company you picked, built live in 90 seconds."*
5. If it failed or looks thin, stay on tab 1. Nobody will notice.

**Pre-run (instant, about 2 s):** Builder.ai, plus a few others. Prefer non-geopolitical names. Type the name exactly and click Run with the default settings.

**At the judging table (5:30–6:30):** always offer it. *"Name a company."* Narrate the timeline while it builds.

**Notes:**
- A pure US company mostly comes back clear. That's fine: "it isn't alarmist" is a feature.
- **Moonshot AI is a Sky9 portfolio company, and a Sky9 partner is judging.** Don't volunteer it. If a judge asks for it, frame the result as "exactly what your LPs will ask."

---

## Q&A prep
| Question | Answer |
|---|---|
| How do you stop hallucinations? | The model only proposes quotes. Code checks each quote against the fetched page and drops anything that doesn't match. Rules, not the model, decide severity. |
| How do you prevent future info leaking into as-of runs? | Telem `published_before` on every query; undated pages only via Internet Archive snapshots captured before the date; watchlist hits must be listed by then. We also tell the model the cutoff, but we never rely on that alone. |
| Why not Orbis, World-Check or Sayari? | They answer "what's true now" for known entities. We found no product that rebuilds a multi-regime risk picture as of a past date. Sayari has time-stamped records, and consultancies (FTI) do manual lookbacks. We'd partner for data. |
| Ownership percentages aren't public. | Correct. We say "aggregate test undetermined" and name the shareholders to ask about. That *is* the diligent inquiry. |
| Is 1260H a sanction? | No: it's a Pentagon procurement ban, not an investment ban. Binding prohibitions (OFAC SDN, NS-CMIC) are tiered red. |
| Isn't $25K/yr a guess? | Yes, it's a pricing hypothesis. The anchor is that today's alternative is analyst days and outside-counsel hours per deal. We'd validate with design partners. |
| Cost per look-through? | About $0.25–0.35 in search credits for a 5-entity run, with cached replays free. Compare that with analyst hours. |
| Can other agents use this? | Yes. It ships as an MCP server: `time_travel_search`, `verify_quote`, `screen_entity`. Show `docs/claude-code-demo.md`: Claude Code answered as of Dec 2025, verified a quote on an archived page, and refused to claim what it couldn't source. |
| Why Telem? | Routing across about 11 engines plus WeChat and LinkedIn, date filtering, fetch fallback, sessions and monitors behind one API. The best single engine found only 38% of our historical evidence. |

**Before saying any number on stage, check it:** the teammate should confirm the COINS Act dates and the 1260H procurement-ban dates (FY2024 NDAA Sec. 805). The Manus facts come from the tool's cited sources and can be clicked through live.

---

## 90-second demo video (for the Devpost "Video demo link")
1. On the Mac: press **Cmd+Shift+5**, choose "Record Selected Portion", select the browser window and click Record.
2. Follow the script above in shortened form, about 20 seconds per section, saying the lines out loud. Skip the business section.
3. Stop with the ⏹ button in the menu bar. Upload to YouTube as **Unlisted** and paste the link into Devpost.

## Submission checklist (due 4:45pm)
- [ ] Name, pitch, About, Built-with: copy from `SUBMISSION.md`
- [ ] Try-it links: demo URL and GitHub
- [ ] 3 images from `media/`
- [ ] YouTube video link
- [ ] Keep this laptop **awake and online** through judging. The public link runs from it. Run `caffeinate -d` in a terminal to stop it sleeping.
