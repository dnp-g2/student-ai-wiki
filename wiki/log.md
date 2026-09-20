---
tags: [meta, log]
---
# Log

## 2026-06-01 · Initialized v3 (Plugin Architecture)
- Created plugin structure: .claude-plugin/ + skills/ + commands/
- 5 modular skills: wiki-core, wiki-ingest, wiki-lint, wiki-review, exam-prep
- 4 slash commands: /ingest /lint /review /exam-prep
- Hot cache + manifest deduplication + token budget rules
- Ready for the first ingest

## 2026-09-20 · English-Only Conversion
- Translated the docs, agent instructions, skills, commands, dashboard labels, and wiki templates into English.
- Removed the duplicate translations. New pages and the glossary are now written in English.
- Translated the setup guide in the source folder, a one-time exception the user approved. Course materials and the manifest were left alone.
- Nothing was ingested or reviewed.

## 2026-09-20 · Shared CLI Instructions
- Made root AGENTS.md the shared instruction entry point for Claude Code CLI and OpenAI Codex CLI.
- Set the minimum supported Claude Code CLI version to 2.1.277.
- Added Codex skill discovery and consolidated Claude skill/command discovery onto the canonical directories through three relative directory symlinks (`.claude/skills`, `.claude/commands`, `.agents/skills`). New skills are exposed to both CLIs automatically.
- Removed other tool integrations and updated setup and architecture documentation for the two supported CLIs.
- Home.md now lists all five operations as plain-text requests that work in both CLIs.
- Updated the setup guide wording in the source folder to name the supported CLIs, a one-time exception the user approved. Course materials and the manifest were left alone.
- Nothing was ingested or reviewed.

## 2026-09-20 · Provenance-Tracked Filing for Ingest
- `ingest` now takes the location of a file anywhere on disk. `scripts/file_source.py` copies it to `raw/{course}/{type-folder}/YYYY-MM-DD-{type}-{slug}.{ext}`, and the destination is proposed to the user before the copy.
- Defined seven source types, each with its own folder: lecture, tutorial, assignment, exam, reading, notes, admin.
- `raw/.manifest.json` (version 2) records the original path, original filename, SHA-256, size, course, type, and date of every filed source, next to the wiki pages it produced. SHA-256 replaces the `md5sum` step, which macOS does not ship.
- `raw/` is now described as append-only: filed sources are never edited, renamed, or deleted. Files already sitting in `raw/` are registered in place.
- Source pages gain `source_type` and `original_name` frontmatter; ingest log entries gain a `Source:` provenance line.
- An original path under the home directory is recorded as `~/...`, so a committed manifest or log carries no username.
- Added `tests/test_file_source.py` for the filing script.
- Rewrote the setup guide in the source folder to describe the new workflow, part of the change the user approved. The manifest holds no sources yet.
- Nothing was ingested or reviewed.

## 2026-09-20 · Tracker for Assessments, Deadlines and Grades
- Added `wiki/tracker/`: one page per assignment, quiz, exam or to-do, with due date, time, weight, status, mark, hurdle, linked concepts and sources. `Dashboard.md` shows the whole semester and `_config.md` holds timezone, term dates and the default target grade.
- Added `scripts/tracker.py` (standard library only) with `add`, `update`, `done`, `mark`, `plan`, `target`, `list`, `focus`, `brief`, `grades`, `hot`, `ics` and `check`. It owns every date calculation, priority score and grade figure.
- Big items get a start-by date and milestones sized by weight. Exams linked to weak concepts produce dated `review` and `exam-prep` suggestions.
- `ics` writes `calendar/student-wiki.ics` with reminders; `--publish-gist` is an opt-in upload to a secret gist.
- Sessions open with a tracker briefing (AGENTS.md rule plus a Claude Code SessionStart hook). `hot.md` gained an Upcoming section.
- Ingest proposes the assessments found in course outlines, assignment specs and exam notices. Lint runs the tracker health check. Review and exam-prep start from the next exam's weak concepts.
- Added the `wiki-tracker` skill, the `/tracker` and `/due` commands, and `tests/test_tracker.py`.
- Nothing was ingested or reviewed.
