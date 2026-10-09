---
name: "Part 1: Europe, Middle East, Australia, UK & Portugal"
cron: "17 9 * * 5"
recurring: true
runs: "Fri 09:17 local time"
discord_channel: "1485242054274711563"  # #tenders
---
Search for large-scale architecture and masterplanning tenders across Europe, Middle East, UK and Portugal and post a digest to Discord channel 1485242054274711563 (#tenders).

This is Part 1 of 3 in the weekly tender scan. Parts 2 (Africa/MDBs) and 3 (Asia/LatAm/Nordics) follow at 10:00 and 10:45.

**What to look for:**
Focus on: masterplanning, mixed-use, civic/cultural buildings, urban design, public realm, developer competitions, university campuses, hospital developments, ideas competitions, framework/roster agreements. Both governmental and private clients are fine. Skip: small single-family residential, pure engineering/MEP, maintenance contracts, geodetic surveying, cleaning/FM services. Do NOT filter by value alone — small competitions with prestige or EOIs with no stated value are worth including if the typology fits.

**Search each region:**

1. **Europe (TED API)** — Run `python scripts/ted_search.py 8 250000` in Bash. This queries the EU Official Journal API directly for architecture/masterplanning tenders published in the last 8 days, filtered to contracts ≥ €250k. Use the script output as the Europe section — it returns title, client, country, deadline, value, TED link, and a ⚠️ flag for deadlines within 21 days. Apply your own judgment to filter out anything that is clearly pure MEP, single-family, or geodetic surveying. Keep everything else: social housing, civic buildings, hospital developments, campus masterplans, urban design studies.

2. **Middle East** — Use multiple sources:
   - Fetch https://etimad.sa/Tender/AllTendersForVisitor and web search "etimad.sa architecture masterplan design consultant 2026" for Saudi government tenders
   - Fetch https://www.tejouri.gov.ae/en/tenders for UAE federal tenders; also web search "tejouri architecture design consultant tender 2026"
   - Web search "architecture masterplan RFP tender Saudi Arabia UAE Qatar Kuwait 2026 site:zawya.com OR site:meed.com OR site:arabianbusiness.com"
   - Web search "NEOM architecture design consultant RFP 2026" and "Vision 2030 masterplan architecture tender 2026"
   - **Private GCC developer portals** — Web search "[developer name] architecture design RFP consultant 2026" for each: Qatari Diar, Msheireb Properties, Red Sea Global, Diriyah Gate Authority, Aldar Properties, Eagle Hills
   - **Qatar** — Fetch https://www.ashghal.gov.qa/en/Tenders and web search "Ashghal architecture design consultant RFP 2026"; also web search "Qatar masterplan architecture tender RFP 2026"
   - **Egypt** — Web search "Egypt architecture masterplan design consultant tender RFP 2026 site:ungm.org OR site:devex.com OR site:zawya.com"; also web search "New Administrative Capital Egypt architecture RFP 2026"
   - **Oman** — Fetch https://tenderboard.gov.om/en/tenders and web search "Oman architecture masterplan design consultant RFP tender 2026"
   - **Bahrain** — Web search "Bahrain Tender Board architecture masterplan design consultant 2026 site:tenderboard.gov.bh OR site:zawya.com"
   - **Kuwait** — Fetch https://www.ctc.gov.kw/en/tenders and web search "Kuwait architecture masterplan design consultant tender RFP 2026 site:ctc.gov.kw OR site:zawya.com"
   - **Turkey** — Fetch https://www.ekap.kik.gov.tr/EKAP/ and web search "Turkey Istanbul architecture masterplan urban design consultant tender RFP 2026"
   - **Iraq** — Web search "Iraq reconstruction architecture urban design consultant RFP 2026 World Bank USAID site:devex.com OR site:ungm.org"; also web search "Baghdad Basra Iraq masterplan architecture design RFP 2026"
   - **MEED Projects** — Web search "site:meed.com architecture masterplan design consultant RFP 2026"; also check arabianbusiness.com and zawya.com/projects

3. **Australia** — Fetch https://www.austender.gov.au/tender/ns/government-atm-search?status=Open and web search "architecture masterplan RFP tender Australia 2026 site:tenders.net OR site:tenderlink.com". Also check NSW and Victorian government portals.

4. **UK & Portugal** — Web search "architecture masterplan RFP Find a Tender UK 2026" and fetch https://www.find-tender.service.gov.uk/Search?hasKeyword=true&keyword=masterplan+architecture. **Portugal** — Fetch https://www.base.gov.pt and web search "Portugal architecture masterplan urban design consultant RFP tender concurso 2026 Lisboa Porto"

5. **Western Balkans & South Caucasus** — EU candidate countries not covered by TED. Single web search pass only (lower density market — don't spend context on portal fetches):
   - **Serbia** — Web search "Serbia Belgrade architecture masterplan urban design consultant tender RFP 2026 site:ujn.gov.rs OR site:ebrd.com"
   - **Georgia** — Web search "Georgia Tbilisi architecture masterplan urban design consultant RFP 2026 site:procurement.gov.ge OR site:ebrd.com OR site:devex.com"
   - **Albania** — Web search "Albania Tirana architecture masterplan urban design consultant RFP 2026 EU IPA site:app.e-albania.al OR site:devex.com"
   Note: Bulgaria, Romania, Hungary, Croatia, Slovenia are EU members — already covered by the TED API above.

**Deadline check:** Fetch the last 30 messages from Discord channel 1485242054274711563 and scan for any tenders mentioned in previous digests. If any have a deadline within the next 14 days that haven't been explicitly passed on, flag them at the top of the post under **⏰ Approaching deadlines**.

**For each new opportunity found, extract and display:**
- **Bold project name** — 1-line description
- Client/issuer & location
- 💰 Estimated value (if known)
- 📅 Deadline (specific date; flag ⚠️ if within 21 days)
- ⏱️ **Effort** — `EOI/RFQ` / `Ideas competition` / `Full design competition` / `Service contract` / `PQ/Shortlist`
- 📋 **Stage** — `EOI open` / `PQ submission` / `Shortlist stage` / `Design submission` / `Registration only`
- 🔗 Source URL
- **Fit rating:** 🟢🟢🟢 Perfect / 🟢🟢⚪ Good / 🟢⚪⚪ Partial / ⚪⚪⚪ Weak

**Post to Discord channel 1485242054274711563 with:**
- Header: 🏗️ **Weekly Tenders — [Date] · Part 1: Europe, Middle East & Australia**
- If any approaching deadlines: **⏰ Approaching deadlines** section first
- A **🏃 Low-effort shortlist** section (EOI/RFQ/PQ opportunities only)
- Opportunities grouped by region (Europe / Middle East / Australia / UK & Portugal)
- Footer: *Part 1 of 3 · Parts 2 (Africa & MDBs) and 3 (Asia/LatAm/Nordics) follow shortly.*

Quality over quantity — 3–5 strong leads per region. Skip anything you're uncertain about.
