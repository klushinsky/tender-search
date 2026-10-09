# Tender Search

Weekly scan for large-scale architecture and masterplanning tenders, run by Claude Code and posted as a digest to Differential's `#tenders` Discord channel.

Every Friday morning it runs three regional passes. Each pass searches public procurement portals, development bank notices, developer RFPs and competition listings, filters for work that fits Differential, and posts a structured digest with a fit rating, effort level and deadline flags.

**Agents picking this up:** start with [AGENTS.md](AGENTS.md).

## Schedule

| Part | Runs (Warsaw time) | Coverage |
|---|---|---|
| 1 | Fri 09:17 | Europe (TED API), Middle East and GCC developers, Australia, UK, Portugal, Western Balkans, South Caucasus |
| 2 | Fri 10:00 | Development banks (World Bank, EBRD, IsDB, AFD, GIZ, UN-Habitat, Devex) and Africa by country, plus Ukraine reconstruction |
| 3 | Fri 10:45 | Asia and Pacific (incl. ADB, Central Asia), South America (incl. IDB), Switzerland and Nordics, invited and PQ-only competitions |

Part 1 also re-reads the last 30 posts in `#tenders` and flags anything with a deadline in the next 14 days.

## What it looks for

**In scope:** masterplanning, mixed-use, civic and cultural buildings, urban design, public realm, developer competitions, university campuses, hospital developments, ideas competitions, framework and roster agreements. Public and private clients.

**Out of scope:** small single-family residential, pure engineering or MEP, maintenance contracts, geodetic surveying, cleaning and FM services.

The TED pass drops contracts with a stated value under €250k. Everywhere else, value is not a hard filter, so small prestige competitions and EOIs with no stated value still come through if the typology fits.

## Digest format

Each opportunity is posted with:

- Project name and a one-line description
- Client or issuer, and location
- Estimated value, if known
- Deadline, flagged ⚠️ if within 21 days
- Effort: `EOI/RFQ`, `Ideas competition`, `Full design competition`, `Service contract` or `PQ/Shortlist`
- Stage: `EOI open`, `PQ submission`, `Shortlist stage`, `Design submission` or `Registration only`
- Source link
- Fit rating from 🟢🟢🟢 (perfect) to ⚪⚪⚪ (weak)

Each post opens with a low-effort shortlist (EOI, RFQ and PQ opportunities only), then groups the rest by region. The target is 3 to 5 strong leads per region rather than volume.

## Repo layout

```
prompts/
  01-europe-middle-east-australia.md      Part 1 prompt + cron schedule
  02-africa-development-banks.md          Part 2 prompt + cron schedule
  03-asia-latam-nordics-competitions.md   Part 3 prompt + cron schedule
scripts/
  ted_search.py                           TED (EU Official Journal) API query used by Part 1
tests/
  test_ted_search.py                      Offline tests for the TED script
AGENTS.md                                 Handover guide for any coding agent
CLAUDE.md                                 Claude Code runtime instructions
```

## Running it

The TED script on its own (Python 3.8+, no dependencies, no API key):

```
python scripts/ted_search.py 8 250000          # last 8 days, min €250k
python scripts/ted_search.py 14 0 --json       # last 14 days, no value filter, JSON output
python -m unittest discover -s tests -v        # offline tests
```

The full scan: open Claude Code in the repo folder with the Discord plugin connected and ask it to run a part ("run tender scan part 1") or to schedule all three. It does not schedule anything on its own.

## Status

The live scans still run from the Discord agent setup at `E:\GitHub\Discord`, which has its own older copies of these prompts and of the script. This repo was extracted from it on 9 October 2026 and cleaned up. [AGENTS.md](AGENTS.md) explains how to switch the live setup over and lists open issues.

### Changes from the original setup

- `ted_search.py` now pages through all results. Before, it sent no page size, so it only got back the API's first page.
- The `min_value_eur` argument (`250000` in Part 1) is now applied. Before, it was ignored.
- Deadline warnings (⚠️ within 21 days), notice-type labels and deadline sorting are now in the script output, as Part 1's prompt already assumed.
- Titles keep any dashes that are part of the real title. Before, splitting on " - " could cut them short.
- Literal "2026" in all 65 search queries replaced with a `{year}` placeholder.
- Part 1's header and region grouping now include all regions it actually searches.
- `--json` output and offline tests added.
