---
tags: [home]
---
# 🏠 Student LLM Wiki

> Your slides go in, your wiki comes out. Read it in Obsidian and let the AI keep it up to date.

## ⚡ Commands

| Command | Purpose |
|---|---|
| `/ingest raw/COMPXXXX/L1.pdf` | Turn slides into notes (files you already added are skipped) |
| `/lint` | Check the wiki for problems and flag concepts you have not reviewed lately |
| `/review COMPXXXX` | Get quizzed on a course |
| `/exam-prep COMPXXXX` | Get practice questions on your weak concepts |

> Put your course PDFs in `raw/{course-code}/`, then run `/ingest`. The course overview is created for you.

## 📚 Courses

```dataview
TABLE file.mtime AS "Last Updated"
FROM "wiki/courses"
SORT file.mtime DESC
```

## 🔴 Weak Concepts

```dataview
TABLE courses, confidence, last_reviewed
FROM "wiki/concepts" WHERE confidence = "low"
SORT last_reviewed ASC
```

## 🟡 Due for Review (20+ Days Since You Last Looked)

```dataview
TABLE courses, last_reviewed
FROM "wiki/concepts"
WHERE confidence = "medium" AND (date(today) - date(last_reviewed)).days > 20
SORT last_reviewed ASC
```

## 🏝️ Pages Nothing Links To

```dataview
LIST FROM "wiki/concepts" WHERE length(file.inlinks) = 0
```

## 📈 Recent Updates

```dataview
TABLE updated FROM "wiki" WHERE updated SORT updated DESC LIMIT 8
```
