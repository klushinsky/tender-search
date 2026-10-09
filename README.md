# Tender Search

Weekly scan for large-scale architecture and masterplanning tenders, run by Claude Code and posted as a digest to Differential's `#tenders` Discord channel.

Every Friday morning it runs three regional passes. Each pass searches public procurement portals, development bank notices, developer RFPs and competition listings, filters for work that fits Differential, and posts a structured digest with a fit rating, effort level and deadline flags.

## Schedule

| Part | Runs (local time) | Coverage |
|---|---|---|
| 1 | Fri 09:17 | Europe (TED API), Middle East and GCC developers, Australia, UK, Portugal, Western Balkans, South Caucasus |
| 2 | Fri 10:00 | Development banks (World Bank, EBRD, IsDB, AFD, GIZ, UN-Habitat, Devex) and Africa by country, plus Ukraine reconstruction |
| 3 | Fri 10:45 | Asia and Pacific (incl. ADB, Central Asia), South America (incl. IDB), Switzerland and Nordics, invited and PQ-only competitions |

Part 1 also re-reads the last 30 posts in `#tenders` and flags anything with a deadline in the next 14 days.

## What it looks for

**In scope:** masterplanning, mixed-use, civic and cultural buildings, urban design, public realm, developer competitions, university campuses, hospital developments, ideas competitions, framework and roster agreements. Public and private clients.

**Out of scope:** small single-family residential, pure engineering or MEP, maintenance contracts, geodetic surveying, cleaning and FM services.

Value is not used as a hard filter outside the TED API pass (which uses a €250k floor), so small prestige competitions and EOIs with no stated value still come through if the typology fits.

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
CLAUDE.md                                 Tells Claude Code to schedule the prompts on session start
```

Each prompt file has a small frontmatter block (`cron`, `discord_channel`) followed by the exact prompt Claude runs. Edit the prompt files to change sources, filters or output format.

## Running it

1. Clone the repo, e.g. to `E:\GitHub\tender-search`.
2. Open Claude Code in the repo folder with the Discord plugin connected.
3. On start, `CLAUDE.md` tells Claude to schedule the three Friday crons from `prompts/`.
4. To run a pass on demand, ask Claude to "run tender scan part 1" (or 2, 3).

The TED script on its own:

```
python scripts/ted_search.py <days_back> <min_value_eur>
python scripts/ted_search.py 8 250000
```

## Where this came from

The prompts were extracted from sections 5, 5b and 5c of `E:\GitHub\Discord\CLAUDE.md` (last edited 27 April 2026). That file still schedules the same three crons for the Discord agent, so only run one of the two setups at a time or `#tenders` gets duplicate posts. To hand over to this repo, remove sections 5, 5b and 5c from the Discord `CLAUDE.md`.

The only change from the original prompts: Part 1 now calls `scripts/ted_search.py` instead of `C:/Users/p/.claude/ted_search.py`.

## Known issues

- **Hardcoded year.** Most web search queries include "2026". They need updating (or switching to "current year") before January 2027 or results will skew to stale notices.
