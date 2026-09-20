# 📂 Filed Course Sources

Files in `raw/` are filed for you. Tell your CLI (Claude Code or Codex) where the file is:

```
ingest ~/Downloads/Lecture3-Attention.pdf
```

The AI proposes a destination, and after your go-ahead `scripts/file_source.py` copies the file here as `raw/{COURSE}/{type-folder}/YYYY-MM-DD-{type}-{short-description}.{ext}`. The original location, original filename, and SHA-256 are recorded in `raw/.manifest.json`.

---

## Folder Guide

| Course folder | Course |
|--------|------|
| `COMP4337/` | Network Security |
| `COMP6713/` | Natural Language Processing (NLP) |
| `COMP9417/` | Machine Learning |
| `INFS5730/` | Social Media Analytics |
| `misc/` | Other materials |

| Type folder | What goes there |
|--------|------|
| `lectures/` | Lecture slides, lecture transcripts |
| `tutorials/` | Tutorial and lab sheets, worked solutions |
| `assignments/` | Assignment and project specs |
| `exams/` | Past exams, quizzes, sample papers |
| `readings/` | Textbook chapters, papers, articles |
| `notes/` | Your own notes |
| `admin/` | Course outline, syllabus, rubrics |

---

> `raw/` is append-only. A filed source is never edited, renamed, or deleted.
