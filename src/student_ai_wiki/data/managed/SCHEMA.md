# SCHEMA: Design Reference

> A human-readable reference.
> Shared project instructions live in `AGENTS.md`; operational rules live in the skills.

## How It Works

This project supports Claude Code CLI (minimum version **2.1.277**) and OpenAI Codex CLI and implements a student version of the Karpathy LLM Wiki pattern. Both CLIs use the root `AGENTS.md` as their single project instruction entry point.

The `student-wiki` tool is installed once per machine (`pipx install student-ai-wiki`) and a vault is created with `student-wiki init`. The tool writes identical copies of each skill to `.claude/skills/` and `.agents/skills/`, which gives both CLIs native discovery, and writes the Claude slash commands to `.claude/commands/`. `student-wiki upgrade` refreshes those files, `AGENTS.md` and this file after a tool update, and leaves `wiki/`, `raw/`, `Home.md` and `.obsidian/` alone. `.student-wiki/state.json` records the tool version that last wrote the vault.

| Layer | Contents | Location |
|---|---|---|
| Layer 1: Sources | Filed sources, append-only, with provenance in `raw/.manifest.json` | `raw/{course}/{type}/` |
| Layer 2: Knowledge | AI-maintained wiki | `wiki/` |
| Layer 3: Rules | Modular skills | `.claude/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md` |

## Skills (Load on Demand to Save Tokens)

| Skill | Trigger | Purpose |
|---|---|---|
| `wiki-core` | Always load first | Architecture + token budget rules + page formats |
| `wiki-ingest` | "ingest" + a file location | File the source into `raw/` (`student-wiki file`), deduplicate, create concept pages |
| `wiki-lint` | "lint" / "check" | Health check + confidence decay |
| `wiki-review` | "review" | Feynman questions + update confidence |
| `exam-prep` | "exam-prep" | Generate questions for weak concepts |
| `wiki-diagram` | "diagram" | Add Mermaid diagrams to concept pages |
| `wiki-tracker` | "add deadline" / "due" / "grades" / "calendar" | Assessments, deadlines, to-dos, grade what-if, session briefing, `.ics` feed (`student-wiki tracker`) |

## Requests and Claude Slash Commands

Both CLIs accept plain-text requests: `ingest [file]`, `lint`, `review [course]`, `exam-prep [course]`, `diagram [concept]`, `add deadline [details]`, `due`, `grades [course]`, and `calendar`.

Claude Code additionally exposes `/ingest [file]`, `/lint`, `/review [course]`, `/exam-prep [course]`, `/diagram [concept]`, `/tracker [request]`, and `/due [course]`. These slash commands are not portable to Codex; use the plain-text requests there.

## Why Split into Skills?

A monolithic SCHEMA was loaded in full on every operation (3000+ tokens). Splitting it into skills loads only the relevant operation rules, such as ingest or lint. Combined with the `wiki/hot.md` cache, this significantly reduces token usage.
