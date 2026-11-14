# LookThrough: 3-minute final presentation

**Setup before you go on:**
- Open http://localhost:8077 full-screen in Chrome, zoomed to 90%. Use the local server, not the tunnel, in case the venue wifi fails.
- Click **Manus AI · Known today** once so it's cached.
- Show the QR code on a phone or a slide: `media/qr-demo.png`. It points to the public replay link.

**Roles:** one person speaks while the other drives the mouse. Rehearse the clicks twice.

---

## 0:00–0:25 · Hook: a person, a moment, a problem (speaker, no clicks)
> "Meet the deal team at a US venture fund. Term sheet signed with a hot AI startup: Singapore address, founders from Beijing, Chinese investors on the cap table. Investment committee is Thursday.
> Since 2025, US law says they must make a **'reasonable and diligent inquiry'** before investing, and it's judged on what they could have known **on the day they signed**. Get it wrong and it's criminal penalties.
> Today that inquiry is days of analysts and outside counsel, stitched together from scattered searches. Plain AI search makes it worse: it leaks the future and invents connections.
> We built **time-travel search**: time-bounded, quote-verified, and it builds the ownership graph. Here's the real case: Meta and Manus."

## 0:25–1:05 · The look-through (driver: "Known today" view, Manus graph)
> "This is LookThrough on Manus. Starting from one name, it discovered who really stands behind the company: the Singapore entity, the Beijing operating company, and investors Tencent and IDG. Every link was found live on the web."

*Click **Tencent**.*
> "Every claim carries a verbatim quote, and we check that quote against the source page. On this run, 100% of claims verified. The model only extracts; deterministic rules make the call. For example, Tencent is on the Pentagon's 1260H list. We label that honestly as a **procurement ban, not an investment ban**, with its listing date."

## 1:05–1:50 · The killer feature: time travel (driver: top switch → **"Knowable on 2025-12-29"**)
> "Now we go back to **December 29, 2025, the day before Meta announced.** LookThrough re-ran the whole investigation using only evidence published before that date. Undated pages only get in through archived snapshots from before that date."

*Point at the yellow banner and the timeline.*
> "Even then, three entities were flagged:
> - Tencent on the 1260H list since January 2025;
> - a Treasury review of the Benchmark-led round;
> - an AI company whose PRC shareholders have undisclosed stakes, so the 50% ownership test needed a cap table.
> All of it was public. The back office could have known. The front office went ahead. **This is the decision record.**"

*Drag the timeline slider slowly to the right* to show later actions appearing: MOFCOM probe, deal blocked, unwind.

## 1:50–2:30 · Powered by Telem (point at the bottom-right panel)
> "Three search primitives make this work: time-bounded retrieval, verified retrieval and connected retrieval. And none of it works on a single search engine. Telem routes every question to the engines suited to it: company questions to Exa, You.com and Linkup, filings questions to Perplexity and Tavily.
> **In the time-travel run, the best single engine found only 38% of the verified evidence. Telem's routing found the rest.**
> Telem's `published_before` filter is what makes time travel possible. WeChat surfaced Chinese-language reporting on who co-led the latest round. Every look-through is one Telem session, which is the audit trail, and one click turns a flag into an hourly Telem Monitor."

## 2:30–3:00 · Who pays and how big (driver: click **"Who it's for →"** at top right)
> "Daily user: the deal team. Budget holder: the General Counsel, who needs a defensible record for every deal.
> Last year: 15,352 US venture deals, $320 billion, 65% of it into AI, the sector this rule covers. There are about 3,000 US venture firms. At $25K a year, that's a $75M beachhead before PE, secondaries, corporate M&A and banks. Treasury's expanded rule lands by March 2027.
> I spent years doing this by hand in hedge-fund compliance. Scan the QR code and try time travel yourself."

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
