---
name: wiki-tracker
description: Track assignments, quizzes, exams, deadlines, to-dos and grades in the wiki. This skill should be used when the user says "add deadline", "what's due", "due", "tracker", "brief", "mark", "grades", "what do I need on the final", "calendar", "to-do", or reports a due date, a mark, or a finished assignment. Also used during ingest of a course outline, assignment spec or exam notice to propose the assessments found in it. Runs student-wiki tracker for every date, score, grade figure and calendar entry.
---

# Wiki Tracker

One place for every assessment, deadline, exam and to-do, with a session briefing, a calendar feed and grade what-if.

## Purpose

Every date, sort order, priority score, grade figure and calendar entry comes from `student-wiki tracker`. Pass the student's values to the script and report what it prints. Each command prints one JSON object with a `status`; `brief` prints text. Add `--dry-run` to any writing command to preview it.

## Item Format

File: `wiki/tracker/{COURSE}-{slug}.md` (a to-do without a course: `todo-{slug}.md`). The filename is the item id and never changes; `title` can be edited freely. Create items with the script so they land in this folder with this frontmatter:

```yaml
---
tags:
  - tracker
  - comp9417
type: assignment        # assignment | quiz | lab | exam | presentation | other | todo
course: COMP9417
title: Assignment 2
due: 2026-10-12
due_time: "23:59"       # empty for an all-day item
weight: 20              # percent of the course grade
status: todo            # todo | doing | done | graded | dropped
start_by: 2026-10-02    # computed from the weight
mark:
out_of:
hurdle:                 # minimum percent required on this item
duration_min:           # exam length; due and due_time are then the start
concepts:
  - "[[Gradient-Descent]]"
sources:
  - "[[2026-09-01-admin-course-outline]]"
needs_check: []         # fields the source left uncertain
created_at: 2026-09-20
---
```

The body holds `## Milestones` (checkboxes with `[due:: YYYY-MM-DD]`) and `## Notes`. Students edit fields and tick milestones in Obsidian; the script reads those edits. `done` means submitted or sat, `graded` means a mark is recorded, `dropped` means it does not count. Overdue is derived from the date.

## Add by Request

Example: "add deadline COMP9417 assignment 2 due 12 Oct 23:59 worth 20%".

1. Turn the request into flags. Ask for the course when a non-todo item has none
2. Preview:
   ```
   student-wiki tracker add --type assignment --course COMP9417 --title "Assignment 2" --due 2026-10-12 --time 23:59 --weight 20 --dry-run
   ```
3. Show the student the echoed due date with its weekday, the start-by date and the milestones, and wait for the go-ahead. For a relative date ("next Friday"), state the calendar date you chose and have the student confirm it
4. Run the same command without `--dry-run`
5. `exists`: the item is already tracked. Offer `update` with the new details

Optional flags: `--concepts A,B`, `--source {source-page}`, `--hurdle 40`, `--out-of 50`, `--duration-min 120`, `--start-by DATE`, `--needs-check due_time,weight`, `--plan none`. To-dos take `--type todo`, with `--course` and `--due` optional.

## Extract During Ingest

For `admin`, `assignment` and `exam` sources, after the source page exists:

1. List every assessment the source names in one table: Item, Type, Due, Time, Weight, Hurdle, Concepts, Uncertain
2. Copy a date or weight only when it is printed in the source. Leave unknown fields blank and name them in the Uncertain column
3. A week-relative date ("Week 7 Friday") needs the term start. Read `term_start` from `wiki/tracker/_config.md`; when it is empty, ask the student, save it there, and state the calendar date you derived
4. Show the table and wait for the student's corrections and go-ahead
5. Run `add` for each row with `--source {source-page}` and `--needs-check` for its uncertain fields. On `exists`, run `update {id} --add-source {source-page}` plus any new details (a course outline followed later by the assignment spec is the usual case)
6. Record the item ids as `tracker_items` in the source's manifest entry

## Update, Complete, Record a Mark

```
student-wiki tracker update {id} --due 2026-10-19 --status doing
student-wiki tracker update {id} --clear due_time --add-concept Entropy --add-source {source-page}
student-wiki tracker done {id}
student-wiki tracker mark {id} 17 --out-of 20
```

Find an id with `list --course COMP9417`. Changing `due` or `weight` recomputes `start_by` and clears those names from `needs_check`. When the output warns that milestone dates are unchanged, offer `plan {id}`. After `mark`, show the course standing from `grades`.

## Plan Milestones

`add` sizes milestones by weight: none under 10%, three steps from 10%, five steps from 25%, and a review, practice, timed-practice sequence for exams. `plan {id}` regenerates the unticked steps and keeps ticked ones; `plan {id} --steps "Outline;Build;Submit"` uses the student's own steps. To tick a step for the student, change `- [ ]` to `- [x]` on that line with a local edit.

## Link Concepts

Link each exam and assignment to the concepts it covers, from the spec's topic list or the exam scope: at most 8 per item, existing concept pages only. These links drive the Exam readiness line, the priority score, and the order of `review` and `exam-prep`.

## Grades and What-if

```
student-wiki tracker grades --course COMP9417
student-wiki tracker grades --course COMP9417 --target 85 --what-if COMP9417-final=70
student-wiki tracker target COMP9417 75
```

`target` stores `target_grade` in the course overview; `no_overview` means the overview needs creating first (wiki-ingest Course Overview Format). Report `average`, `required_average` and the `outcome` (`on_track`, `secured`, `unreachable`, `missed`, `no_target`, `weights_over_100`). Mention `untracked_weight` when it is above zero, every failed hurdle, and the `unweighted` items. For best-N-of-M schemes, set the items that do not count to `dropped`.

## Briefing

`student-wiki tracker brief` prints overdue items, the next 14 days, work to start now, milestones, exam readiness, the top-priority item, grades, and fields to confirm. Run it at session start (see AGENTS.md) and whenever the student asks what is due. Relay its lines as printed. When Exam readiness names weak concepts, offer the `review` and `exam-prep` runs it lists by their dates. `brief --course COMP9417` narrows it to one course.

## Calendar

```
student-wiki tracker ics
```

This writes `calendar/student-wiki.ics`: one event per dated item, plus start-by and milestone events, with alarms scaled by weight. Run it again after tracker changes; a re-import updates the same events.

- Apple Calendar: File → Import. Alarms are kept. When subscribing to a published feed, untick "Remove alerts"
- Google Calendar: Settings → Import & export. Google ignores alarms inside calendar files, so have the student set default notifications on that calendar
- Outlook: Add calendar → Upload from file

Set `timezone` (for example `Australia/Sydney`) in `wiki/tracker/_config.md` so timed deadlines convert correctly; `tz_mode: floating` in the output means times are written as local wall-clock times.

Publishing is opt-in: `ics --publish-gist` uploads the feed to a secret GitHub gist through the `gh` CLI and prints a `subscribe_url` for calendar apps. Anyone who has that URL can read the deadlines, so run it only at the student's request. `publish_failed` means the local file was still written; relay `publish_error`.

## Meta Updates

After tracker changes, once at the end:

- `student-wiki tracker hot` rewrites the `## Upcoming` section of `wiki/hot.md`
- Append to `wiki/log.md`: `## {YYYY-MM-DD} · tracker: added N, updated N, graded N`

## Token Rule

Answer date, priority and grade questions from `list`, `brief`, `focus` and `grades` output. Open a tracker page only to edit its notes or tick a milestone.
