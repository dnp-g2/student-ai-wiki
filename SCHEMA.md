# SCHEMA: Design Reference

> This file is now a human-readable reference only.
> The actual operating rules live in the `skills/` directory.

## How It Works

This Claude Code / Cowork plugin implements a student version of the Karpathy LLM Wiki pattern.

| Layer | Contents | Location |
|---|---|---|
| Layer 1: Sources | Read-only slides | `raw/{course}/` |
| Layer 2: Knowledge | AI-maintained wiki | `wiki/` |
| Layer 3: Rules | Modular skills | `skills/*/SKILL.md` |

## Skills (Load on Demand to Save Tokens)

| Skill | Trigger | Purpose |
|---|---|---|
| `wiki-core` | Always load first | Architecture + token budget rules + page formats |
| `wiki-ingest` | "ingest" / drop in slides | Ingest slides, deduplicate, create concept pages |
| `wiki-lint` | "lint" / "check" | Health check + confidence decay |
| `wiki-review` | "review" | Feynman questions + update confidence |
| `exam-prep` | "exam-prep" | Generate questions for weak concepts |

## Commands (Slash Commands)

`/ingest [file]` · `/lint` · `/review [course]` · `/exam-prep [course]`

## Why Split into Skills?

A monolithic SCHEMA was loaded in full on every operation (3000+ tokens). Splitting it into skills loads only the relevant operation rules, such as ingest or lint. Combined with the `wiki/hot.md` cache, this significantly reduces token usage.
