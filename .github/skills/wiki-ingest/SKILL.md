---
name: wiki-ingest
description: Digest a course source file into the wiki. This skill should be used when the user says "ingest", "process this PDF/slide", or drops a course file into raw/ and wants it turned into wiki pages. Reads the source, deduplicates via manifest, creates source + concept pages, and finds cross-course connections.
---

# Wiki Ingest

Turn a source file in `raw/` into wiki pages.

## Steps

1. **Deduplicate**: Compute the file hash with `md5sum {file} | cut -d' ' -f1`. Check `raw/.manifest.json`; skip matching hashes and report "Already processed; use force to ingest again"
2. **Read context**: Read `wiki/hot.md` (not the entire SCHEMA)
3. **Locate existing pages**: Read `wiki/index.md` to find related concept pages
4. **Read the source** and extract 3–5 key takeaways
5. **Discuss with the user and confirm** (do not skip this step)
6. **Create a source page** `wiki/sources/{name}.md`
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

## Manifest Format

```json
{
  "sources": {
    "raw/COMP6713/L3.pdf": {
      "hash": "abc123",
      "course": "COMP6713",
      "ingested_at": "2026-06-01",
      "pages_created": ["wiki/sources/L3.md"],
      "concepts_created": ["Attention-Mechanism"],
      "concepts_updated": ["Transformer"],
      "connections_found": 2,
      "contradictions_found": 0
    }
  }
}
```

## Batch Ingest

Process multiple files individually, but update index/hot/log/manifest **only once after the entire batch**. Report progress after every 10 files.

## Completion Report

"Processed N sources. Created X pages and updated Y pages. Cross-course connections found: ..."

## Course Overview Format

File: `wiki/courses/{COURSE}-overview.md`
```markdown
---
tags: [course-overview, {course-code}]
course: {COURSE-CODE}
updated: YYYY-MM-DD
---
# {COURSE-CODE} · {Course Name}

## Summary
{Describe the course topic in one sentence}

## Concept Map
[[Concept-A]] · [[Concept-B]] · ...

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
- Created concepts: [[Concept-A]], [[Concept-B]]
- Updated concepts: [[Concept-C]]
- Cross-course connections: N (see connections-log.md)
- Contradictions: N (see contradictions.md)
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
