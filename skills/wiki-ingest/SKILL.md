---
name: wiki-ingest
description: Digest a course source file into the wiki. This skill should be used when the user says "ingest", "process this PDF/slide", or gives the location of a course file and wants it turned into wiki pages. Files the source into raw/ with a provenance record, deduplicates via manifest, creates source + concept pages, and finds cross-course connections.
---

# Wiki Ingest

File a source into `raw/` with its provenance, then turn it into wiki pages.

## File the Source

The user gives the location of a file anywhere on disk. `scripts/file_source.py` copies it into `raw/`, renames it, hashes it, and records where it came from. Files enter `raw/` only through this script.

**Destination**: `raw/{COURSE}/{type-folder}/YYYY-MM-DD-{type}-{slug}.{ext}`

| Type | Folder | What it is |
|---|---|---|
| `lecture` | `lectures/` | Lecture slides, lecture transcripts |
| `tutorial` | `tutorials/` | Tutorial and lab sheets, worked solutions |
| `assignment` | `assignments/` | Assignment and project specs |
| `exam` | `exams/` | Past exams, quizzes, sample papers |
| `reading` | `readings/` | Textbook chapters, papers, articles |
| `notes` | `notes/` | The student's own notes |
| `admin` | `admin/` | Course outline, syllabus, rubrics, announcements |

Pick the type by what the file is. Use the course code as `{COURSE}`, or `misc` for material outside any course. The date is the content date (lecture date, exam session); the script falls back to a `YYYY-MM-DD` prefix in the filename, then to today. The slug is a short lowercase description; the script derives it from the original filename unless `--slug` is given.

1. **Locate**: Infer course, type, date, and slug from the path, the filename, and a skim of the document. Ask the user when the course or the type is unclear
2. **Propose**: Run the script with `--dry-run` and show the user `{original path} → {raw path}`. Wait for the go-ahead; a name in `raw/` is permanent
   ```
   python3 scripts/file_source.py "{path}" --course COMP6713 --type lecture [--date YYYY-MM-DD] [--slug text] --dry-run
   ```
3. **File**: Run the same command without `--dry-run` and read the JSON it prints:
   - `filed`: copied and recorded; continue with `raw_path`
   - `registered`: the file already lived in `raw/`; it was recorded in place; continue
   - `duplicate` with `"ingested": true`: report "Already processed; use force to ingest again" and stop
   - `duplicate` with `"ingested": false`: the content is filed and awaiting ingest; continue with the existing `raw_path`
   - An "already exists" error: propose a different `--slug`; never overwrite

## Steps

1. **File the source** as described above (do not skip this step, and do not copy files into `raw/` by hand)
2. **Read context**: Read `wiki/hot.md` (not the entire SCHEMA)
3. **Locate existing pages**: Read `wiki/index.md` to find related concept pages
4. **Read the source** from its `raw/` copy and extract 3–5 key takeaways. `.pdf`, `.md`, and `.txt` read directly. `.docx` and `.pptx` are zip archives: extract the text first (for example `unzip -p "{file}" word/document.xml`, or a document-reading skill when the CLI has one)
5. **Discuss with the user and confirm** (do not skip this step)
6. **Create a source page** `wiki/sources/{name}.md`
6.2. **Extract assessments** (for `admin`, `assignment`, and `exam` sources): follow "Extract During Ingest" in the wiki-tracker skill. Propose the assessments found in the source as a table, copy dates and weights only as printed, wait for confirmation, then add them with `scripts/tracker.py add --source {source-page}`
6.5. **Create/update the course overview** `wiki/courses/{COURSE}-overview.md`:
   - If missing, create it using the Course Overview Format below
   - Otherwise, append wiki links for new concepts to the Concept Map section
7. **Create/update concept pages** (at most 3–5 pages; keep the scope focused):
   - New concept → create `wiki/concepts/{Name}.md`, default confidence to low, and **set `created_at` to today's date**
   - Existing concept → make local edits, add content, and update `last_reviewed` (do not change `created_at`)
8. **Handle diagrams**: Describe important source diagrams in prose. For processes, architecture, sequences, classifications, or other visual concepts, apply the wiki-diagram criteria to add Mermaid diagrams
9. **Cross-course connections**: Check whether new concepts appear in other courses. If so:
   - Add reciprocal wiki links to both concept pages
   - Append an entry to `wiki/connections-log.md` using the Connection Log Format below
10. **Detect contradictions**: If new content conflicts with existing pages:
    - Mark the concept page with a `> [!contradiction]` callout
    - Append an entry to `wiki/contradictions.md` using the Contradiction Format below
11. **Update once at the end**: `index.md` + `hot.md` + `log.md` + `overview.md` + `.manifest.json` (not after each step)
    - In `overview.md`, add new courses to the course list, update Cross-Course Connections for new links, and update Contradictions for new conflicts
    - Append new concepts to `wiki/glossary.md` using the columns Term, Domain, and Page (English term, domain, and wiki link)
    - Append a structured entry to `log.md` using the Log Entry Format below
    - In `.manifest.json`, add the wiki fields to the entry the script created; leave its provenance fields unchanged
    - When tracker items were added or changed, run `python3 scripts/tracker.py hot` to refresh the `## Upcoming` section of `hot.md`

## Manifest Format

`scripts/file_source.py` writes the provenance fields (`sha256` through `filed_at`) when it files the source. It records a path under the home directory as `~/...`; copy `original_path` from the script's output into `log.md` as printed, and never expand it to an absolute path. Step 11 adds the rest. An entry with `filed_at` and no `ingested_at` is filed and awaiting ingest.

```json
{
  "version": 2,
  "sources": {
    "raw/COMP6713/lectures/2026-06-01-lecture-attention.pdf": {
      "sha256": "9f2c…",
      "size_bytes": 1830211,
      "course": "COMP6713",
      "type": "lecture",
      "date": "2026-06-01",
      "original_path": "~/Downloads/L3 (final).pdf",
      "original_name": "L3 (final).pdf",
      "filed_at": "2026-06-01T09:14:02Z",
      "ingested_at": "2026-06-01",
      "pages_created": ["wiki/sources/L3.md"],
      "concepts_created": ["Attention-Mechanism"],
      "concepts_updated": ["Transformer"],
      "tracker_items": [],
      "connections_found": 2,
      "contradictions_found": 0
    }
  }
}
```

## Batch Ingest

Propose all destinations in one table and get one go-ahead, then file each source with the script. Process the files individually, but update index/hot/log and the manifest's wiki fields **only once after the entire batch**. Report progress after every 10 files.

## Completion Report

"Processed N sources. Created X pages and updated Y pages. Tracker items added: N. Cross-course connections found: ..."

## Course Overview Format

File: `wiki/courses/{COURSE}-overview.md`
```markdown
---
tags: [course-overview, {course-code}]
course: {COURSE-CODE}
target_grade:
updated: YYYY-MM-DD
---
# {COURSE-CODE} · {Course Name}

## Summary
{Describe the course topic in one sentence}

## Concept Map
[[Concept-A]] · [[Concept-B]] · ...

## Assessments
\`\`\`dataview
TABLE WITHOUT ID file.link AS "Item", type AS "Type", due AS "Due", weight AS "Weight %", status AS "Status", mark AS "Mark", out_of AS "Out of"
FROM "wiki/tracker"
WHERE course = "{COURSE-CODE}" AND type != "todo"
SORT due ASC
\`\`\`

## Weak Areas
\`\`\`dataview
TABLE confidence, last_reviewed FROM "wiki/concepts"
WHERE contains(courses, "{COURSE-CODE}") AND confidence = "low"
SORT last_reviewed ASC
\`\`\`

## Sources
\`\`\`dataview
LIST FROM "wiki/sources" WHERE contains(tags, "{course-code}") SORT file.ctime DESC
\`\`\`
```

## Connection Log Format

Append to `wiki/connections-log.md`:
```markdown
## {YYYY-MM-DD} · {Concept Name}
**Course A**: {COURSE-A} → [[Concept-Page-A]]
**Course B**: {COURSE-B} → [[Concept-Page-B]]
**Connection**: Explain in one sentence why these two concepts are related
**Depth**: Surface similarity / Shared mathematical foundation / Different applications of the same idea
```

## Log Entry Format

Append to `wiki/log.md`:
```markdown
## {YYYY-MM-DD} · ingest: {source-file}
- Source: `{original_path}` → `{raw_path}` ({size_bytes} bytes, sha256 {first 8 characters})
- Created concepts: [[Concept-A]], [[Concept-B]]
- Updated concepts: [[Concept-C]]
- Cross-course connections: N (see connections-log.md)
- Contradictions: N (see contradictions.md)
- Tracker items: [[COMP6713-assignment-2]] (omit the line when there are none)
```

## Contradiction Format

Append to `wiki/contradictions.md`:
```markdown
## {YYYY-MM-DD} · {Contradiction Title}
**Page A**: [[page-a]] says "..."
**Page B**: [[page-b]] says "..."
**Tension**: Describe the nature of the contradiction
**Status**: Unresolved
**Resolution**: (To be filled in)
```
