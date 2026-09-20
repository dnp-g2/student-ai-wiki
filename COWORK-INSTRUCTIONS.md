# Student Wiki Maintainer

Read raw/ slides, compile into wiki/. Never modify raw/. Read SCHEMA.md on first run.

## Token Rules (Highest Priority)
1. Read only wiki/hot.md first at each session start (≤500 words)
2. Read wiki/index.md only if more context is needed
3. Read at most 3–5 existing pages per ingest
4. Make local edits; do not rewrite entire pages
5. For batch operations, update index/hot/log once at the end
6. Before ingest, check raw/.manifest.json; skip files with matching hashes

## Architecture
raw/{course}/ ← Read-only slides
wiki/hot.md ← Context cache, read first each session
wiki/index.md ← Master catalog
wiki/concepts/ ← Concept pages (Feynman style, English-only, 100–300 lines)
wiki/sources/ ← Source summaries
wiki/courses/ ← Course map of content
wiki/exam-prep/ ← Practice questions

## Workflows
INGEST: Check manifest for duplicates → read hot → read index → read source → discuss with user → create source and concept pages (3–5 pages) → update index/hot/log/manifest once at the end → check cross-course connections and contradictions
QUERY: Read hot → read index → read relevant pages (≤5) → synthesize an answer → ask whether to save it
LINT: Orphans + broken links + contradictions + stale content + confidence decay (lower one level after >30 days without review) + missing cross-course links
REVIEW: Feynman questions → adjust confidence and last_reviewed → generate questions for low-confidence concepts → wiki/exam-prep/
EXAM-PREP: Scan concepts → sort by confidence → generate questions for low/medium-confidence concepts

## Concept Page Frontmatter
tags:[concept,{domain}] courses:[{codes}] confidence:{low|medium|high} last_reviewed:{date}

## Domain Rules
Mathematics: LaTeX + intuition | Security: attack/defense pairs + lab verification ✅ | ML: use cases + comparisons | NLP: architecture + distinguish pretraining and fine-tuning

## Language: English only; use English names with hyphens for wiki links
