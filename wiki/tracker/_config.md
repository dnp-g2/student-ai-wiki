---
tags: [meta, tracker-config]
timezone:
term_start:
term_end:
default_target:
alarms: true
brief_days: 14
---
# Tracker Settings

> Fill these in once per term. `scripts/tracker.py` reads them from the properties above.

| Setting | Meaning | Example |
|---|---|---|
| `timezone` | Your IANA timezone, used for today's date and for timed deadlines in the calendar feed | `Australia/Sydney` |
| `term_start` | First day of week 1, used for "Week 3 of 12" and week-relative due dates | `2026-09-14` |
| `term_end` | Last day of term | `2026-12-04` |
| `default_target` | Target grade for courses that have none on their overview page | `75` |
| `alarms` | Put reminders inside calendar events | `true` |
| `brief_days` | How far ahead the session briefing looks | `14` |
