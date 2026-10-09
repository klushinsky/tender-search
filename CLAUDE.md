# Tender Search: session instructions

This repo runs Differential's weekly tender scan for architecture and masterplanning work. It is meant to be opened in Claude Code with the Discord plugin connected.

## On session start

Silently, without waiting for input, schedule one recurring cron per file in `prompts/`:

1. Read each `prompts/*.md` file.
2. Call CronCreate with:
   - cron: the `cron` value from the file's frontmatter
   - recurring: true
   - prompt: everything below the closing `---` of the frontmatter, verbatim
3. Do not announce this to the user.

Do not schedule these if the same tender crons are already running from another session (for example the `E:\GitHub\Discord` setup), or #tenders will get duplicate posts.

## Running a part manually

When asked to "run the tender scan" (or a specific part), execute the prompt body of the matching file in `prompts/` directly instead of waiting for the cron.

## Discord replies

Messages from Discord arrive in a `<channel source="plugin:discord:discord" ...>` tag. Always reply with the `mcp__plugin_discord_discord__reply` tool, never as terminal text. Before replying in #tenders (1485242054274711563), fetch the last 5 messages from the channel for context.

## Paths

Run from the repo root. The TED script is `scripts/ted_search.py`.
