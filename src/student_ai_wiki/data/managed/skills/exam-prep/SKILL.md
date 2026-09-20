---
name: exam-prep
description: Generate practice exam questions from weak concepts. This skill should be used when the user says "exam-prep", "make practice questions", "generate a quiz", or is preparing for an exam in a specific course. Scans concept pages, prioritizes low-confidence ones, and writes a practice question set.
---

# Exam Prep: Practice Questions

Generate practice questions from weak concepts.

## Steps

1. Read `wiki/index.md` to find all concept pages for the target course
2. Read their frontmatter and sort by `confidence` (low first). Run `student-wiki tracker focus {COURSE}`; concepts linked to the next exam or quiz go ahead of others at the same confidence
3. Generate 1–2 questions for each low/medium-confidence concept
4. Save to `wiki/exam-prep/{course}.md`

## Question Types

Mix the following types; do not use only recall questions:
- **Application**: Give a scenario and ask which method to use and why
- **Comparison**: Ask about differences between two related concepts and their use cases
- **Derivation** (mathematics/ML): Ask for a derivation or explanation of a formula
- **Attack and defense** (security): Give an attack and ask for defenses, or vice versa
- **Trap questions**: Target common misconceptions

## Page Format

```markdown
---
tags: [exam-prep, {course}]
generated: YYYY-MM-DD
based_on: [concept-pages]
for_item: "[[{tracker-item-id}]]"   # optional: the exam or quiz this set prepares for
---
# {Course} Practice Questions

## Q1: {Concept Name} (confidence: low)
**Question**: ...
**Reference Answer**: ...
**Related Page**: [[concept]]
```

## Principles

- Prioritize concepts with confidence:low
- Link each question to its concept page for review
- Provide complete reference answers, but encourage the user to answer first

## Language

Use English only for all questions, reference answers, headings, and feedback.
