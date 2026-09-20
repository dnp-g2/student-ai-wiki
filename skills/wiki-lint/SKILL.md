---
name: wiki-lint
description: Health-check the wiki and apply confidence decay. This skill should be used when the user says "lint", "check the wiki", or wants to find orphan pages, broken links, contradictions, or stale concepts. Runs the 30-day confidence decay rule and reports issues for the user to fix.
---

# Wiki Lint

Health-check the knowledge base.

## Checks

1. **Orphans**: Concept pages with no incoming wiki links
2. **Broken links**: Wiki links pointing to nonexistent pages
3. **Contradictions**: Conflicting descriptions of a concept across pages. Record them in `wiki/contradictions.md` using the wiki-ingest Contradiction Format and update the contradiction summary in `overview.md`
4. **Stale content**: Pages with confidence:low that have not been updated for a long time
5. **Confidence Decay**:
   - If `last_reviewed` is more than 30 days ago and no new page has referenced the concept in that period → lower confidence by one level (high→medium→low)
   - List all downgraded concepts
6. **Missing cross-course links**: The same concept appears in multiple courses without reciprocal links
7. **Missing overviews**: Check that each course in `index.md` has a `wiki/courses/{course}-overview.md`; automatically create missing overviews using the wiki-ingest Course Overview Format
8. **Glossary gaps**: Add missing entries for existing concept pages to `wiki/glossary.md`, using the English-only Term, Domain, and Page columns
9. **Tracker health**: Run `python3 scripts/tracker.py check` and report its groups: overdue items and milestones, items missing a date or weight, course weights that do not add up to 100, exams within 21 days that have weak or no linked concepts, broken concept and source links, fields waiting for confirmation, finished items with no mark, misplaced and unreadable tracker pages. Fix them through the wiki-tracker commands

## Process

1. Read `wiki/index.md` for the page list
2. Read pages as needed for checks (respect token budgets and work in batches)
3. Report findings and **ask the user which issues to fix** (do not automatically fix everything)
4. After repairs, perform batch maintenance (update directly without further confirmation):
   - `wiki/courses/{course}-overview.md` (create missing course overviews)
   - `wiki/glossary.md` (add missing glossary entries)
   - `wiki/contradictions.md` (append newly discovered contradictions)
   - `wiki/connections-log.md` (record missing cross-course connections)
   - `wiki/overview.md` (synchronize contradiction summaries, connection summaries, and the course list)
   - `wiki/hot.md` Upcoming section (run `python3 scripts/tracker.py hot`)
   - `wiki/log.md` (append using: `## {YYYY-MM-DD} · lint: orphans N, broken links N, decayed N, contradictions N, links added N, overviews added N, terms added N, tracker issues N`)

## Report Format

```
🏝️ Orphans (N): ...
🔗 Broken links (N): ...
⚡ Contradictions (N): ...
📉 Confidence decay (N): [Concept] high→medium (not reviewed for 45 days)
🌉 Missing cross-course links (N): [Concept A] and [Concept B] should link to each other
📂 Missing course overviews (N): wiki/courses/{course}-overview.md
📖 Missing glossary entries (N): [Concept Name]
⏰ Overdue items (N): [item id] due YYYY-MM-DD
📅 Items missing a date or weight (N): [item id]
⚖️ Course weights off 100 (N): [COURSE] totals 80
🧠 Exams with weak linked concepts (N): [item id]: [Concept Name]
❓ Tracker fields to confirm (N): [item id]: due_time
🧾 Other tracker issues (N): broken links, missing marks, misplaced or unreadable pages
```
