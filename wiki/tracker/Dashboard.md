---
tags: [meta, tracker-dashboard]
---
# 🗓️ Tracker Dashboard

> Every assignment, exam, deadline and to-do in one place. Ask the AI `due` for a prioritized briefing, `grades COMP9417` for what you need on the rest, and `calendar` for the reminder feed.

## 🔥 Overdue

```dataview
TABLE WITHOUT ID file.link AS "Item", course AS "Course", due AS "Due", weight AS "Weight %", status AS "Status"
FROM "wiki/tracker"
WHERE type AND due AND due < date(today) AND (status = "todo" OR status = "doing")
SORT due ASC
```

## ⏰ Due in the Next 14 Days

```dataview
TABLE WITHOUT ID file.link AS "Item", course AS "Course", due AS "Due", due_time AS "Time", weight AS "Weight %", status AS "Status"
FROM "wiki/tracker"
WHERE type AND due AND due >= date(today) AND due <= date(today) + dur(14 days) AND (status = "todo" OR status = "doing")
SORT due ASC
```

## 🚀 Start Now

```dataview
TABLE WITHOUT ID file.link AS "Item", start_by AS "Start by", due AS "Due", weight AS "Weight %"
FROM "wiki/tracker"
WHERE type AND start_by AND start_by <= date(today) AND status = "todo"
SORT due ASC
```

## 🪜 Milestones

```dataview
TASK
FROM "wiki/tracker"
WHERE !completed AND meta(section).subpath = "Milestones"
SORT due ASC
```

## 📆 Whole Semester

```dataview
TABLE WITHOUT ID month AS "Month", rows.file.link AS "Item", rows.due AS "Due", rows.weight AS "Weight %", rows.status AS "Status"
FROM "wiki/tracker"
WHERE type AND due AND status != "dropped"
SORT due ASC
GROUP BY dateformat(due, "yyyy-MM") AS month
SORT month ASC
```

## 📊 Marks So Far

```dataview
TABLE WITHOUT ID course AS "Course", sum(rows.weight) AS "Graded %", round(sum(map(rows, (r) => r.weight * r.mark / r.out_of)), 1) AS "Points banked"
FROM "wiki/tracker"
WHERE type AND mark != null AND weight AND out_of AND status != "dropped"
GROUP BY course
```

Ask `grades COMP9417` for your average, hurdles, and the mark you need on the remaining work to reach your target.

## ✅ To-dos Without a Date

```dataview
LIST
FROM "wiki/tracker"
WHERE type = "todo" AND !due AND (status = "todo" OR status = "doing")
```

## ❓ Details to Confirm

```dataview
TABLE WITHOUT ID file.link AS "Item", needs_check AS "Check these fields"
FROM "wiki/tracker"
WHERE type AND needs_check AND length(needs_check) > 0
```
