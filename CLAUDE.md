# Tender Search: Claude Code instructions

@AGENTS.md

The guide above covers what this repo is, the file layout and the rules for editing. This file only adds Claude Code specifics.

## Do not auto-schedule

Do **not** schedule the scans on session start. Most sessions in this repo are development work, and the live scans currently run from the Discord agent at `E:\GitHub\Discord`. Scheduling here as well would double-post to `#tenders`.

## Scheduling the scans (only when Piotr asks)

When asked to start or schedule the tender scan from this repo:

1. Confirm the same crons are not running from the Discord agent.
2. For each `prompts/*.md` file, call CronCreate with `cron` from the frontmatter, `recurring: true`, and the prompt body (everything after the closing `---`) verbatim.
3. Report which three crons were created and when they fire.

## Running a part on demand

When asked to "run tender scan part 1" (or 2, 3), execute the body of the matching prompt file now. If Piotr only wants to preview it, print the digest in the terminal and don't post to Discord.

## Discord replies

If a message arrives in a `<channel source="plugin:discord:discord" ...>` tag, reply with the `mcp__plugin_discord_discord__reply` tool, never as terminal text.

## Paths

Run from the repo root. The TED script is `scripts/ted_search.py`; tests are `python -m unittest discover -s tests -v`.
