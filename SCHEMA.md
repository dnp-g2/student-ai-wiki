# SCHEMA: Design Reference

> This file is now a human-readable reference only.
> Shared project instructions live in `AGENTS.md`; operational rules live in the `skills/` directory.

## How It Works

This project supports Claude Code CLI (minimum version **2.1.277**) and OpenAI Codex CLI and implements a student version of the Karpathy LLM Wiki pattern. Both CLIs use the root `AGENTS.md` as their single project instruction entry point.

Canonical skills live in `skills/`. `.claude/skills` and `.agents/skills` are relative symlinks to `skills/`, which gives both CLIs native discovery from one copy of the rules. `.claude/commands` is a relative symlink to `commands/`. The `.claude-plugin/` metadata preserves optional Claude plugin packaging; Codex does not use that packaging. Repository-local usage requires no plugin installation.

| Layer | Contents | Location |
|---|---|---|
| Layer 1: Sources | Filed sources, append-only, with provenance in `raw/.manifest.json` | `raw/{course}/{type}/` |
| Layer 2: Knowledge | AI-maintained wiki | `wiki/` |
| Layer 3: Rules | Modular skills | `skills/*/SKILL.md` |

## Skills (Load on Demand to Save Tokens)

| Skill | Trigger | Purpose |
|---|---|---|
| `wiki-core` | Always load first | Architecture + token budget rules + page formats |
| `wiki-ingest` | "ingest" + a file location | File the source into `raw/` (`scripts/file_source.py`), deduplicate, create concept pages |
| `wiki-lint` | "lint" / "check" | Health check + confidence decay |
| `wiki-review` | "review" | Feynman questions + update confidence |
| `exam-prep` | "exam-prep" | Generate questions for weak concepts |
| `wiki-diagram` | "diagram" | Add Mermaid diagrams to concept pages |

## Requests and Claude Slash Commands

Both CLIs accept plain-text requests: `ingest [file]`, `lint`, `review [course]`, `exam-prep [course]`, and `diagram [concept]`.

Claude Code additionally exposes `/ingest [file]`, `/lint`, `/review [course]`, `/exam-prep [course]`, and `/diagram [concept]`. These slash commands are not portable to Codex; use the plain-text requests there.

## Why Split into Skills?

A monolithic SCHEMA was loaded in full on every operation (3000+ tokens). Splitting it into skills loads only the relevant operation rules, such as ingest or lint. Combined with the `wiki/hot.md` cache, this significantly reduces token usage.
