---
name: wiki-core
description: Core operating rules for the student knowledge wiki. This skill should be used whenever working inside an Obsidian vault that contains a wiki/ folder with hot.md, or when the user mentions ingest, lint, review, exam-prep, or asks to build/maintain their course knowledge base. Loads the three-layer architecture, token budget rules, and English-only page formats. Always loads first.
---

# Student LLM Wiki: Core

You maintain a student knowledge wiki. Read `raw/`, write `wiki/`. Never modify `raw/`.

## Three-Layer Architecture

```
raw/{course}/    ← Layer 1: Read-only slides
wiki/            ← Layer 2: Knowledge you maintain
  hot.md         ←   Context cache (≤500 words), READ FIRST
  index.md       ←   Master catalog
  overview.md    ←   Cross-course synthesis
  log.md         ←   Append-only log
  courses/       ←   Course map of content
  concepts/      ←   Concept pages (core)
  sources/       ←   Source pages
  exam-prep/     ←   Practice questions
raw/.manifest.json  ← Dedup tracker
(These skills are Layer 3: operating rules)
```

## Token Budget Rules (TOP PRIORITY)

Violating these wastes the user's quota. They override all other rules.

1. **Read only `wiki/hot.md` first at each session start** (≤500 words). If it provides the needed context, do not read other pages
2. **Read `wiki/index.md` only if more context is needed**, then use it to locate pages
3. **Read at most 3–5 existing pages per ingest**. More than five is too broad
4. **Make local edits; do not rewrite entire pages** to change a single field
5. **Keep wiki pages to 100–300 lines**. Split pages longer than 300 lines
6. **For batches, update index/hot/log once at the end**, not after each source

## Language

Use English only for prose, headings, templates, questions, feedback, and diagram labels. Use English names with hyphens for wiki links (e.g. `[[Gradient-Descent]]`).

## Concept Page Format

File: `wiki/concepts/{English-Name}.md`
```yaml
---
tags: [concept, {domain}]
courses: [COMP6713]
confidence: low|medium|high
last_reviewed: YYYY-MM-DD
created_at: YYYY-MM-DD
---
```
Sections: Intuition (Feynman style) → Detailed → [Diagram, optional; see wiki-diagram skill] → Why → Connections (including cross-course links) → Sources → Open Questions

## Course Overview Format

File: `wiki/courses/{COURSE}-overview.md`, frontmatter: `tags: [course-overview, {course-code}]` + `course: {COURSE-CODE}` + `updated: YYYY-MM-DD`
Sections: Summary (one sentence) → Concept Map (list of wiki links) → Weak Areas (Dataview: confidence=low) → Sources (Dataview: sources by course tag)

## Source Page Format

File: `wiki/sources/{name}.md`
```yaml
---
tags: [source, {course-code}]
course: {COURSE-CODE}
ingested: YYYY-MM-DD
source_file: raw/{course}/{filename}
---
```
Sections: Key Takeaways (3–5) → Diagram Descriptions (note whether a Mermaid redraw is recommended; see wiki-diagram skill) → New Concepts → Updated Pages

## Hot Cache Contents

After each operation, update `wiki/hot.md` (≤500 words): three most recent sources / recent concepts / current weak concepts / pending tasks

## Domain Rules

- Mathematics: LaTeX + an intuitive explanation of each symbol
- Security COMP4337: pair attacks with defenses; mark lab-verified material ✅
- ML COMP9417: use cases + comparisons + bias–variance characteristics
- NLP COMP6713: architecture descriptions + distinguish pretraining, fine-tuning, and inference
- Analytics INFS5730: SAS VTA steps + data types

## Hard Rules

1. Never modify raw/
2. One concept per page, Feynman style
3. Cross-course connections provide the greatest value
4. Mark uncertainty with confidence:low
5. Token budget rules take precedence
