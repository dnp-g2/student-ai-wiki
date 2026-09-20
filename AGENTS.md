# Student LLM Wiki: Agent Instructions

You maintain this student knowledge wiki. Read `raw/`, write `wiki/`. Never modify `raw/`.

## Supported CLIs and Shared Instructions

- Supported tools: Claude Code CLI **2.1.277 or newer** and OpenAI Codex CLI.
- This root `AGENTS.md` is the single project instruction entry point for both CLIs. Start the CLI from the repository root.
- Canonical operation rules live in `skills/`; load only the relevant skill on demand. `.claude/skills/` and `.agents/skills/` expose those same files for native discovery, not separate rule copies.
- The requests below are plain-text prompts for either CLI. Claude also exposes slash commands through `.claude/commands/`; do not assume those slash commands exist in Codex.

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
raw/{course}/    ← Read-only slides (NEVER modify)
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
