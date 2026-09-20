# Student AI Wiki: Agent Instructions

You maintain this student knowledge wiki. Read `raw/`, write `wiki/`. `raw/` is append-only: sources enter through `student-wiki file`, and a filed source is never edited, renamed, or deleted.

## Supported CLIs and Shared Instructions

- Supported tools: Claude Code CLI **2.1.277 or newer** and OpenAI Codex CLI.
- This root `AGENTS.md` is the single project instruction entry point for both CLIs. Start the CLI from the vault root (the folder that holds this file).
- Operation rules are skills; load only the relevant skill on demand. Each skill is installed at `.claude/skills/<name>/SKILL.md` (Claude Code) and `.agents/skills/<name>/SKILL.md` (Codex). The two copies are identical.
- This file, the skills and the slash commands are installed by the `student-wiki` command-line tool and refreshed by `student-wiki upgrade`. Leave them as installed; the student's own content lives in `wiki/` and `raw/`.
- Every `student-wiki ...` command runs from anywhere inside the vault. If the shell reports that `student-wiki` is missing, ask the student to run `pipx ensurepath` and open a new terminal; never compute tracker dates or grades by hand.
- The requests below are plain-text prompts for either CLI. Claude also exposes slash commands through `.claude/commands/`; do not assume those slash commands exist in Codex.

## Operation Rules

Read the corresponding skill before each operation (load on demand to save tokens):

| Operation | Skill |
|---|---|
| Before any operation | `wiki-core` |
| ingest | `wiki-ingest` |
| lint | `wiki-lint` |
| review | `wiki-review` |
| exam-prep | `exam-prep` |
| diagram | `wiki-diagram` |
| tracker (deadlines, exams, to-dos, grades, calendar) | `wiki-tracker` |

## Token Budget Rules (Highest Priority)

1. **Read only `wiki/hot.md` first at each session start** (≤500 words). Then run `student-wiki tracker brief`, unless a tracker brief is already in context, and open your first reply with its overdue and due-soon lines (at most 5 lines)
2. Read `wiki/index.md` only if more context is needed
3. Read at most 3–5 existing pages per ingest
4. Make local edits; do not rewrite entire pages
5. For batch operations, update index/hot/log once at the end
6. Ingest starts by filing the source with `student-wiki file`; it checks `raw/.manifest.json` and reports content that is already filed

## Architecture

```
raw/{course}/{type}/  ← Filed sources, read-only: YYYY-MM-DD-{type}-{slug}.{ext}
                        (lectures, tutorials, assignments, exams, readings, notes, admin)
student-wiki file     ← Command: copies a source into raw/, renames it, records provenance
student-wiki tracker  ← Command: deadlines, priorities, grades, calendar feed; owns every date calculation
wiki/
  hot.md         ← Context cache, read first
  index.md       ← Master catalog
  concepts/      ← Concept pages
  sources/       ← Source pages
  courses/       ← Course overviews
  exam-prep/     ← Practice questions
  tracker/       ← Assessments, deadlines, exams, to-dos (one page per item)
raw/.manifest.json  ← Provenance + dedup tracker
```

## Commands

- `ingest ~/Downloads/L3.pdf`: File a source from any location into `raw/` (the destination is proposed first, then copied), and ingest it
- `lint`: Health check + confidence decay
- `review COMP9417`: Feynman review
- `exam-prep COMP4337`: Generate questions for weak concepts
- `diagram Attention-Mechanism`: Add a Mermaid diagram to a concept page
- `add deadline COMP9417 assignment 2 due 12 Oct 23:59 worth 20%`: Track an assessment or to-do (previewed first, then written)
- `due`: Briefing of overdue items, the next 14 days, work to start now, and exam readiness
- `grades COMP9417`: Course standing and the mark needed on the remaining work
- `calendar`: Write the `.ics` reminder feed to `calendar/student-wiki.ics`

## Language

Use English only for all generated content, headings, templates, questions, feedback, and diagram labels. Use English names with hyphens for wiki links.
