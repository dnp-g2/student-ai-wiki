# Student LLM Wiki: Project Instructions

You maintain this student knowledge wiki. Read `raw/`, write `wiki/`. Never modify `raw/`.

## Operation Rules

Read the corresponding rules file before each operation (load on demand to save tokens):

| Operation | Rules file |
|---|---|
| Before any operation | `skills/wiki-core/SKILL.md` |
| ingest | `skills/wiki-ingest/SKILL.md` |
| lint | `skills/wiki-lint/SKILL.md` |
| review | `skills/wiki-review/SKILL.md` |
| exam-prep | `skills/exam-prep/SKILL.md` |
| diagram | `skills/wiki-diagram/SKILL.md` |

## Token Budget Rules (Highest Priority)

1. **Read only `wiki/hot.md` first at each session start** (≤500 words)
2. Read `wiki/index.md` only if more context is needed
3. Read at most 3–5 existing pages per ingest
4. Make local edits; do not rewrite entire pages
5. For batch operations, update index/hot/log once at the end
6. Before ingest, check `raw/.manifest.json`; skip files with matching hashes

## Architecture

```
raw/{course}/    ← Read-only slides
wiki/
  hot.md         ← Context cache, read first
  index.md       ← Master catalog
  concepts/      ← Concept pages
  sources/       ← Source pages
  courses/       ← Course overviews
  exam-prep/     ← Practice questions
raw/.manifest.json  ← Dedup tracker
```

## Commands

- `ingest raw/COMP6713/L3.pdf`: Ingest course slides
- `lint`: Health check + confidence decay
- `review COMP9417`: Feynman review
- `exam-prep COMP4337`: Generate questions for weak concepts
- `diagram Attention-Mechanism`: Add a Mermaid diagram to a concept page

## Language

Use English only for all generated content, headings, templates, questions, feedback, and diagram labels. Use English names with hyphens for wiki links.
