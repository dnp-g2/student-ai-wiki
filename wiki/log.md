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
