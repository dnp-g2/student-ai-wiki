# Changelog

All notable changes to this project are recorded here. Releases follow [Semantic Versioning](https://semver.org), and this file is maintained by [release-please](https://github.com/googleapis/release-please) from [Conventional Commits](https://www.conventionalcommits.org).

## History before 0.1.0

Development before the first packaged release carried no tags or version numbers.

- **2026-09-20, tracker.** `wiki/tracker/` with one page per assignment, quiz, exam or to-do; the tracker command with `add`, `update`, `done`, `mark`, `plan`, `target`, `list`, `focus`, `brief`, `grades`, `hot`, `ics` and `check`; start-by dates and milestones sized by weight; the `.ics` calendar feed with opt-in publishing to a secret gist; a session briefing through `AGENTS.md` and a Claude Code SessionStart hook; assessment extraction during ingest; the `wiki-tracker` skill and the `/tracker` and `/due` commands.
- **2026-09-20, provenance-tracked filing.** `ingest` takes a file anywhere on disk and files a renamed copy under `raw/{course}/{type-folder}/`. Seven source types. `raw/.manifest.json` version 2 records original path and name, SHA-256, size, course, type and date. `raw/` became append-only.
- **2026-09-20, shared CLI instructions.** `AGENTS.md` became the single instruction entry point for Claude Code CLI (2.1.277 or newer) and OpenAI Codex CLI, with skill discovery for both.
- **2026-09-20, English-only conversion.** Docs, agent instructions, skills, commands, dashboard labels and wiki templates translated into English.
- **2026-06-01, v3 plugin architecture.** Modular skills (`wiki-core`, `wiki-ingest`, `wiki-lint`, `wiki-review`, `exam-prep`), slash commands, the hot cache, manifest deduplication and token budget rules.
