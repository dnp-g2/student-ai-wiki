# Plan: Tracker subsystem (assessments, to-dos, deadlines, exams)

## Context

Students lose marks to logistics: deadlines scattered across course outlines, LMS pages and
assignment PDFs, no single semester view, and no signal about where effort pays off. The wiki
already files those documents (`assignment`, `exam`, `admin` source types) and already knows which
concepts are weak, yet it extracts no dates or weights and has no notion of a task. This change adds
a tracker that makes the wiki the one place a student looks: every assessment and to-do, a
whole-semester dashboard, reminders through a calendar feed and a session briefing, study planning
tied to concept confidence, grade what-if math, and work-back milestones.

Decisions made with the user:
- Reminders: .ics calendar feed with alarms, plus an in-session briefing.
- v1 scope: core tracker, study planning tied to the wiki, grade tracking and what-if, work-back
  milestones, general to-dos.
- Feed delivery: the script always writes a local .ics file; an opt-in flag publishes it to a
  secret gist through `gh`.

Repo facts that shape the design: the wiki is greenfield (no course or concept pages yet, so no
migration); Dataview is the only Obsidian plugin; skills and commands are auto-exposed to both CLIs
through the `.claude/skills`, `.agents/skills`, `.claude/commands` symlinks; `scripts/file_source.py`
and `tests/test_file_source.py` set the script and test conventions (stdlib only, one JSON object
with `status`, `--root`, `--dry-run`, atomic writes, unittest with subprocess against a temp root).

## Design

### Data model: one page per item in `wiki/tracker/`

Path `wiki/tracker/{COURSE}-{slug}.md` (to-dos without a course: `todo-{slug}.md`). The filename
stem is the permanent item id and the ICS UID base; `title` stays editable. Slug rules reuse
`slugify` from `scripts/file_source.py`.

```yaml
---
tags:
  - tracker
  - comp9417
type: assignment        # assignment | quiz | lab | exam | presentation | other | todo
course: COMP9417
title: Assignment 2
due: 2026-10-12         # Date only, so Obsidian and Dataview date math stay clean
due_time: "23:59"       # empty means all-day
weight: 20              # percent of course grade
status: todo            # todo | doing | done | graded | dropped (overdue is derived)
start_by: 2026-09-28
mark:
out_of: 100
hurdle:
duration_min:           # exams: due + due_time is the start
concepts:
  - "[[Gradient-Descent]]"
sources:
  - "[[2026-09-01-admin-course-outline]]"
needs_check:            # fields the source left uncertain
  - due_time
created_at: 2026-09-20
---
# COMP9417 · Assignment 2

## Milestones
- [ ] Understand the spec and plan [due:: 2026-09-30]
- [ ] First full draft [due:: 2026-10-07]
- [ ] Review and submit [due:: 2026-10-11]

## Notes
```

- Milestones are body checkboxes with an inline `[due:: ]` field: one regex for the script, native
  ticking in Obsidian, and a Dataview `TASK` query renders them.
- Frontmatter is written in Obsidian's block style so Properties UI edits give small diffs. No
  `updated` key (Home.md "Recent Updates" queries `WHERE updated`).
- Settings live in `wiki/tracker/_config.md` frontmatter: `timezone`, `default_target`,
  `term_start`, `term_end`, `alarms`, `brief_days`. It has no `type` key and every query filters on
  `WHERE type`. Per-course `target_grade` lives in the course overview frontmatter.
- Parser: stdlib restricted YAML, flat keys only. Tolerates BOM, CRLF, quotes, flow and block
  lists, bare `[[X]]`, `weight: 20%`, and `due: 2026-10-12T23:59:00` (split into date and time).
  Unknown constructs are preserved and reported by `check`. Writes patch only the changed key
  lines, atomically.

### `scripts/tracker.py` (stdlib only)

All date arithmetic, sorting, scoring, grade math and calendar output come from this script; the
agent passes values in and reports the output. Global flags `--root`, `--today`, `--dry-run`.
`sys.stdout.reconfigure(encoding="utf-8")` at startup for Windows.

| Command | Purpose | `status` |
|---|---|---|
| `add --type --title [--course --due --time --weight --concepts --source --hurdle --out-of --duration-min --needs-check --plan auto\|none]` | create item, compute start-by and milestones | `added`, `proposed`, `exists` |
| `update ID [field flags, --status, --clear, --add-source, --add-concept]` | patch fields | `updated`, `proposed`, `not_found` |
| `done ID` / `mark ID 17 [--out-of 20]` | complete / record a mark (sets `graded`) | `updated` |
| `plan ID [--steps "A;B;C"]` | regenerate unticked milestones | `planned` |
| `target COURSE N` | write `target_grade` into the course overview | `updated`, `no_overview` |
| `list [--course --within --status --type --all]` | query items | `ok` |
| `focus COURSE` | next exam-like item and its concepts, weak first | `ok`, `none` |
| `brief [--days 14 --max 5 --json --hook]` | session briefing text | text |
| `grades [--course --target --what-if ID=85]` | standing and required average | `ok` |
| `hot` | rewrite only `## Upcoming` in `wiki/hot.md`, absolute dates, max 5 lines | `updated`, `unchanged` |
| `ics [--out calendar/student-wiki.ics] [--publish-gist]` | calendar feed | `written`, `unchanged`, `published` |
| `check` | health groups for wiki-lint | `ok` |

**Start-by and milestones.** Lead days by weight: 40+ → 21, 25+ → 14, 15+ → 10, 5+ → 5, under 5 →
2, missing → 7. `start_by = max(due - lead, created_at)`. Weight 10–24 gets three steps (20%, 70%,
due minus 1 day); 25+ gets five (15%, 40%, 70%, 90%, due minus 1 day); exam-like items get "Review
weak concepts (run review)", "Practice set (run exam-prep)", "Timed practice and recap".

**Priority score.** `round(W * U * S * C)`: W = `max(weight, 3)` (10 when missing, flagged); U = 4
when overdue, else `clamp(lead / max(days_left, 0.5), 0.2, 4)`; S = 1.0 todo, 0.7 doing; C =
`min(1 + 0.1 * weak_linked, 1.5)` for exam-like items. A linked concept is weak at confidence low
or medium, stale when `last_reviewed` is over 20 days old (matches the Home.md idiom). The script
reads concept frontmatter itself, costing the agent zero tokens.

**Grades (per course).** Banked points, average on graded weight, untracked weight counted as
remaining, `required_avg = (target - earned) / remaining * 100` with `secured` and `unreachable`
(plus `max_possible`) outcomes, `weights_over_100` warning, unweighted items listed and excluded,
hurdles reported `pending | met | failed` with `at_risk`. `--what-if` applies for one run.
Best-N-of-M is out of scope; the documented workaround is `dropped`.

**Brief** (under 200 words, empty sections omitted, house emoji `(N)` style):

```
📅 Tracker brief · Sun 2026-09-20 · Week 2 of 12
🔥 Overdue (1): COMP9417 Quiz 1 · due Fri 2026-09-18 · 5%
⏰ Due in 14 days (2):
- Mon 2026-09-28 23:59 · 8d · COMP9417 Assignment 1 · 15% · doing
🚀 Start now (1): COMP4337 Project · start-by 2026-09-19 · due 2026-10-19 · 30%
🪜 Milestones (1): 2026-09-23 · COMP9417 Assignment 1 · First full draft
🧠 Exam readiness (1): COMP9417 Midterm in 12d · weak: Gradient-Descent (low) · run `review COMP9417` by 2026-09-25 and `exam-prep COMP9417` by 2026-09-29
🎯 Next: COMP9417 Assignment 1 (score 42)
📊 Grades: COMP9417 78.0% on 20% graded, need 73.5% on the rest for 75
⚠️ Needs checking (1): COMP4337 Project · due_time
```

`--hook` mode prints nothing on an empty tracker, catches every exception, always exits 0.

**ICS.** CRLF, folding at 75 octets on UTF-8 boundaries, TEXT escaping, stable UIDs
(`{id}@student-ai-wiki`, `{id}-start@…`, `{id}-ms-{slug(text)}@…`). Stateless versioning:
`DTSTAMP`/`LAST-MODIFIED` from file mtime, `SEQUENCE = mtime // 60`, so output is a pure function
of the files and a re-import updates events by UID. Timed items convert to UTC through `zoneinfo`
(floating-time fallback when the zone database is missing, reported as `tz_mode`). A deadline is a
30-minute block ending at the due time; an exam runs `duration_min`. Alarms: exam-like or weight
20+ → 7d, 2d, 1d, plus 3h when timed; weight 10–19 → 3d, 1d; otherwise 1d. Start-by and milestone
events are all-day with a 09:00 alarm. Finished items stay without alarms. `calendar/` is
gitignored.

`--publish-gist` (opt-in): first run `gh gist create` (secret) and store the gist id in gitignored
`calendar/.gist-id`; later runs `gh gist edit`. Output includes the raw subscribe URL. Missing or
unauthenticated `gh` returns a clear error and the local file is still written.

Client caveats to document: Apple Calendar keeps alarms on import (untick "Remove alerts" when
subscribing); Google Calendar ignores VALARM, so students set default notifications on that
calendar, and it refreshes subscriptions every 12 to 24 hours.

### Two entry paths for deadlines

- **Ingest extraction** (new step 5.5 in wiki-ingest for `admin`, `assignment`, `exam` sources):
  propose a table (Item, Type, Due, Time, Weight, Hurdle, Concepts, Uncertain), copy only dates
  printed in the source, leave unknowns blank and list them in `needs_check`, resolve
  week-relative dates through `term_start` once the student confirms it, wait for confirmation,
  then `add --source {source-page}`. On `exists`, `update --add-source`. Record `tracker_items` in
  the manifest entry.
- **Plain language**: "add deadline COMP9417 assignment 2 due 12 Oct 23:59 worth 20%" → flags →
  `--dry-run` echo-back → confirm → run.

### Session briefing

- AGENTS.md rule (both CLIs): after reading `wiki/hot.md`, run `python3 scripts/tracker.py brief`
  and open the first reply with its overdue and due-soon lines (max 5).
- `wiki/hot.md` gains `## Upcoming`, maintained by `tracker.py hot`, as the fallback surface.
- Committed `.claude/settings.json` SessionStart hook for Claude Code calling
  `python3 "$CLAUDE_PROJECT_DIR/scripts/tracker.py" brief --hook` (timeout 10). Verify the hook
  schema against current Claude Code docs before committing. Lands in its own late commit.

### Study planning

`focus COURSE` feeds wiki-review (quiz the nearest exam's weak concepts first) and exam-prep
(those concepts sort ahead at equal confidence; optional `for_item` frontmatter). The brief's Exam
readiness line carries dated `review` / `exam-prep` suggestions.

## Files

**New:** `scripts/tracker.py`, `tests/test_tracker.py`, `skills/wiki-tracker/SKILL.md`,
`commands/tracker.md`, `commands/due.md`, `wiki/tracker/_README.md`, `wiki/tracker/_config.md`,
`wiki/tracker/Dashboard.md`, `.claude/settings.json`,
`docs/superpowers/specs/2026-09-20-tracker-design.md` (this design, committed first).

**`skills/wiki-tracker/SKILL.md` sections:** Purpose (script owns every date and figure) → Item
Format → Add by Request → Extract During Ingest → Update, Complete, Record a Mark → Plan
Milestones → Link Concepts (max 8, existing pages only) → Grades and What-if → Briefing → Calendar
(import steps per client, caveats, `--publish-gist`) → Meta updates (`tracker.py hot`, log line
`## {YYYY-MM-DD} · tracker: added N, updated N, graded N`) → Token rule (answer date questions
with `list` or `brief`, never by reading tracker pages).

**Edited:**
- `AGENTS.md`: operation table row, brief rule under token rule 1, architecture tree, command
  examples (`add deadline …`, `due`, `grades COMP9417`, `calendar`).
- `skills/wiki-core/SKILL.md`: architecture tree, course overview format (`target_grade`,
  Assessments section between Concept Map and Weak Areas), short Tracker Item Format pointer, hot
  cache contents, hard rule 6.
- `skills/wiki-ingest/SKILL.md`: step 5.5, step 11 (`tracker.py hot`, `tracker_items`), manifest
  example, course overview template (`target_grade`, `## Assessments` Dataview block), completion
  report.
- `skills/wiki-lint/SKILL.md`: check 9 runs `tracker.py check`; report lines `⏰ Overdue items
  (N)`, `📅 Items missing a date or weight (N)`, `⚖️ Course weights off 100 (N)`, `🧠 Exams with
  weak linked concepts (N)`, `❓ Tracker fields to confirm (N)`; log line gains `tracker issues N`.
- `skills/wiki-review/SKILL.md`, `skills/exam-prep/SKILL.md`: `focus` integration.
- `commands/ingest.md`, `Home.md` (new `## ⏰ Due Soon` block above Courses, dashboard link,
  command rows), `wiki/hot.md`, `wiki/index.md`, `SCHEMA.md`, `README.md` (new "Deadlines, grades
  and calendar" section, commands table, tree, Windows `python3` and `tzdata` note), `.gitignore`
  (`calendar/`), `.claude-plugin/plugin.json` (3.2.0), `wiki/log.md`.

**Dataview views (plain DQL):** Due Soon (14 days, overdue first), Overdue, Start now, Needs
checking, Milestones (`TASK … WHERE !completed AND meta(section).subpath = "Milestones"`),
semester timeline (`GROUP BY dateformat(due, "yyyy-MM")`), grades summary (grouped by course),
per-course Assessments table. Three constructs need checking in Obsidian: grouped `SORT`, the
`map` lambda in the grades table, `meta(section).subpath`. Fallback for the lambda: a
script-written `points` field validated by `check`.

## Commit sequence (branch `feat/tracker`)

1. `docs: add tracker design spec`
2. `feat: add tracker script with item storage and listing` (parser, add, update, done, mark, list)
3. `feat: add tracker brief, priority scoring and milestones` (plus `focus`, `hot`)
4. `feat: add grade standing and what-if to tracker`
5. `feat: generate ics calendar feed from tracker` (plus `--publish-gist`, `.gitignore`)
6. `feat: add tracker health check`
7. `feat: add wiki-tracker skill and commands`
8. `feat: extract assessments during ingest and link tracker to lint, review and exam-prep`
9. `feat: add tracker views to Home, dashboard and course overviews`
10. `feat: brief the student at session start`
11. `docs: document the tracker in README and SCHEMA`, `chore: bump plugin version to 3.2.0`

Each script commit is test-first (`tests/test_tracker.py`, same harness as
`tests/test_file_source.py`).

## Test coverage

Add (canonical frontmatter, dry-run, `exists`, course-less to-do, bad input); date math per weight
band, `created_at` clamp, overdue boundary; round trip of an Obsidian-rewritten fixture (block
lists, quotes, datetime `due`, CRLF, BOM, unknown key) with byte-for-byte assertions outside the
patched lines; grades (standing, secured, unreachable, untracked, over 100, hurdle, what-if,
dropped, `no_overview`); brief (empty line, `--hook` silence and exit 0 on corrupt files, section
order, caps, exam readiness from concept fixtures, score order); ICS (CRLF, 75-octet folding with
multibyte titles, escaping, UID stability across title change and milestone reorder, `unchanged`
on rerun, SEQUENCE after `os.utime`, all-day form, DST conversion for `Australia/Sydney` skipped
when the zone is missing, alarm bands, `alarms: false`); `check` groups; `hot` idempotence.
`--publish-gist` is tested with a stub `gh` on `PATH`.

## Verification

1. `python3 -m unittest discover -s tests`
2. End to end in a temp root: `add` an assignment, an exam with a linked concept fixture and a
   quiz; `mark` the quiz; run `brief --today 2026-09-25`, `grades --course COMP9417 --target 75`,
   `check`, `ics`.
3. Validate the .ics with an iCalendar validator; import into Apple Calendar and confirm alerts;
   change a due date, regenerate, re-import, confirm the event moves without a duplicate; import
   into Google Calendar and confirm events appear.
4. Open the vault in Obsidian: every Dataview block renders; edit a property in the Properties
   UI, run `update`, confirm the file round-trips.
5. Start `claude` in the repo and confirm the brief reaches context; run the plain-language add
   flow and an `ingest` of a sample course outline through the confirmation table.

## Risks and deferrals

- A wrong deadline costs marks. Mitigations: confirmation table, `needs_check`, dates copied only
  from the source, source links on every item.
- Google Calendar cannot deliver ICS alarms; the README says so plainly.
- Windows: `python3` may be absent from PATH (the AGENTS.md rule still covers the brief), `tzdata`
  may be missing (floating times).
- Deferred: plugin-packaged hooks, best-N-of-M, recurring to-dos, archiving finished to-dos,
  weekly timeline grouping.
