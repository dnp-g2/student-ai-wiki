---
description: File a course source into raw/ with provenance, then digest it into the wiki (dedup + concept pages + cross-course links)
argument-hint: [path to the file anywhere on disk, e.g. ~/Downloads/L3.pdf] [course] [type]
---

Use the wiki-ingest skill to process the source file at: $ARGUMENTS

First file the source: infer the course, type, date and slug, run `scripts/file_source.py` with `--dry-run`, show me the proposed `raw/` destination, and copy it after my go-ahead. Then follow the token budget rules from wiki-core. Read hot.md first, discuss key points with me before writing, then create source + concept pages and update meta files once at the end. For a course outline, assignment spec or exam notice, also propose the assessments it names for the tracker and add them after my confirmation.
