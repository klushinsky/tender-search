# AGENTS.md: handover guide for coding agents

Read this before changing anything in this repo. It is written for Claude Code, Codex, Cursor, Gemini or any other agent picking up the work.

## What this project is

An automated weekly scan for **public and private tenders for architecture and masterplanning work**, run for Differential (a computational design and architecture studio working across Poland, the Gulf, Australia and beyond). The output is a digest posted to the `#tenders` Discord channel (ID `1485242054274711563`) that the team uses to decide what to bid on.

There is no server and no database. The "engine" is an LLM agent (Claude Code with the Discord plugin) running three long prompts on a cron schedule. The prompts tell the agent which portals to fetch, which web searches to run, how to filter, and how to format the post. One Python script does a structured query against the EU's TED API, because TED has a proper API and is the highest-volume source.

## Files

| Path | What it is | Edit when |
|---|---|---|
| `prompts/01-europe-middle-east-australia.md` | Part 1 prompt. TED API (via script), GCC portals and developers, Australia, UK, Portugal, Western Balkans, South Caucasus. Also does the approaching-deadline check over past posts. | Adding or removing sources in these regions |
| `prompts/02-africa-development-banks.md` | Part 2 prompt. World Bank, EBRD, IsDB, AFD, GIZ, UN-Habitat, Devex, and African countries plus Ukraine. | Same, for these regions |
| `prompts/03-asia-latam-nordics-competitions.md` | Part 3 prompt. Asia and Pacific, ADB, Central Asia, IDB and South America, Switzerland, Nordics, invited and PQ-only competitions. | Same, for these regions |
| `scripts/ted_search.py` | Queries `api.ted.europa.eu/v3/notices/search` by CPV code, filters and formats. Standard library only. | Changing CPV codes, notice types, keyword filters, output format |
| `tests/test_ted_search.py` | Offline unit tests for the script (API mocked). | Whenever you change the script |
| `CLAUDE.md` | Claude Code runtime instructions (how to schedule and run the scans). | Changing how the scans are launched |
| `README.md` | Human-facing overview. | Keep in sync with any behaviour change |

### Prompt file format

Each prompt file is YAML frontmatter followed by the prompt body:

```
---
name: "Part 1: ..."
cron: "17 9 * * 5"          # standard 5-field cron, local time (Europe/Warsaw)
recurring: true
runs: "Fri 09:17 local time" # human-readable copy of cron
discord_channel: "1485242054274711563"  # #tenders
---
<prompt body, passed verbatim to the agent>
```

Rules for editing prompts:

- **Each prompt must stay self-contained.** The cron fires the body as a fresh instruction, so it cannot rely on the other parts or on this file.
- **Use `{year}` in search queries, never a literal year.** Each prompt tells the agent to substitute the current year. Literal years go stale every January.
- **Keep the per-opportunity fields identical across the three parts** (name, client, value, deadline, Effort, Stage, Source URL, Fit rating). The team scans all three posts together.
- Keep the "quality over quantity, 3 to 5 leads per region" instruction. The digest is useful because it is short.
- If you change the timing of one part, update the cross-references in the other two ("Part 1 posted at 9:17", "follows at 10:45").

## The TED script

```
python scripts/ted_search.py [days_back] [min_value_eur] [--json]
python scripts/ted_search.py 8 250000          # what Part 1 runs
python scripts/ted_search.py 14 0 --json       # for debugging or other agents
python -m unittest discover -s tests -v        # offline tests
```

Behaviour:

- Searches CPV 71200000, 71220000, 71240000, 71400000, 71410000, 71420000; notice types `cn-standard`, `cn-social`, `cn-desg` (design contest), `pin-cfc-social`; `scope: ACTIVE`.
- Pages through all results, 250 per page, capped at 20 pages.
- Drops titles matching `SKIP_KEYWORDS` (pure MEP and civil engineering, in English, German and Swedish).
- `min_value_eur` drops notices whose stated value converts to less than the threshold. Notices with no value, or a currency not in `EUR_PER_UNIT`, are kept on purpose: many good design competitions and EOIs have no stated value.
- `EUR_PER_UNIT` holds rough exchange rates used only for that threshold. Accuracy within about 10% is fine.
- Output is sorted by deadline, soonest first, with ⚠️ on deadlines within 21 days.
- On an HTTP or network error it prints the error plus any partial results, and exits 1 only if nothing came back.
- Forces UTF-8 stdout so Polish characters and emoji don't crash on Windows pipes.

## How it runs today

The live scans run from a **different** place: the Discord agent at `E:\GitHub\Discord` on Piotr's Windows machine. Its `CLAUDE.md` (sections 5, 5b, 5c) contains older inline copies of these three prompts, and Part 1 there calls `C:/Users/p/.claude/ted_search.py`, the pre-cleanup version of the script.

This repo was extracted from that setup on 9 October 2026 and is now the source of truth for the tender scan. Until the Discord setup is switched over to this repo, changes made here **do not affect the live scan**. To switch over:

1. Clone this repo to `E:\GitHub\tender-search`.
2. In `E:\GitHub\Discord\CLAUDE.md`, replace sections 5, 5b and 5c with an instruction to schedule the three prompts from `E:\GitHub\tender-search\prompts\`, and change the script path to `E:/GitHub/tender-search/scripts/ted_search.py`.

Ask Piotr before touching the Discord setup; it runs several other scheduled jobs (morning brief, invoices, grants, reflection).

## Rules for agents working here

- **Never schedule the crons or post to `#tenders` while developing.** Running a scan for real posts to a channel the team reads. To test a prompt, run it and print the digest to the terminal instead of posting, unless Piotr asks for a real post.
- **Don't run both setups at once.** If the scans are scheduled from this repo and from the Discord agent, every digest posts twice.
- Run the unit tests after any script change. They are offline and take under a second.
- The TED API is public and needs no key. Don't add API keys, tokens or Discord bot credentials to this repo. If a future source needs a key, read it from an environment variable and document it here.
- Keep the script dependency-free (standard library only). It runs on Piotr's Windows machine with whatever Python is on PATH.
- Copy style for prompt output is set in the prompts. In any new human-facing text, avoid em dashes (Piotr's preference); use commas, colons or periods.

## Known issues and next steps

- **Not yet verified against the live API after the cleanup.** The fixes (pagination, value filter, deadline flag) are covered by the offline tests, but the first real run should be checked: `python scripts/ted_search.py 8 250000` should report a fetched count well above 10 for a normal week.
- **Inconsistent "What to look for" criteria across parts.** Part 1 includes ideas competitions and framework/roster agreements and says not to filter by value alone. Parts 2 and 3 have a shorter list, and Part 3 explicitly skips fully open competitions. Decide with Piotr whether to unify.
- **No record of what was already posted.** De-duplication relies on the agent reading the last 30 messages in `#tenders` (Part 1 only). A small JSON log of posted TED publication numbers would let the script mark repeats as "seen before".
- **Discord message length.** Digests can exceed Discord's 2,000 character limit, and the prompts don't say how to split them. Check whether posts ever arrive truncated; if so, add a splitting instruction to each prompt.
- **Many portals are fetched as web pages** (Etimad, Tejouri, EKAP, AusTender and others). Some may block or render client-side. Where a portal has an API or RSS feed, a small script like `ted_search.py` is more reliable than a page fetch.
