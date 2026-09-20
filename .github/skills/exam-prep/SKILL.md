---
name: exam-prep
description: Generate practice exam questions from weak concepts. This skill should be used when the user says "exam-prep", "make practice questions", "generate a quiz", or is preparing for an exam in a specific course. Scans concept pages, prioritizes low-confidence ones, and writes a practice question set.
---

# Exam Prep: Practice Questions

Generate practice questions from weak concepts.

## Steps

1. Read wiki/index.md to find all concept pages for the target course
2. Read frontmatter and sort by confidence (low first)
3. Generate 1–2 questions for each low/medium-confidence concept
4. Save to wiki/exam-prep/{course}.md

## Question Types (Mix Types; Do Not Use Only Recall Questions)

- Application: Give a scenario and ask which method to use
- Comparison: Differences and use cases of two related concepts
- Derivation (ML): Ask for a derivation or explanation of a formula
- Attack and defense (security): Give an attack and ask for defenses, or vice versa
- Trap questions: Target common misconceptions

## Principles

- Prioritize confidence:low
- Link each question to its concept page
- Provide complete reference answers and encourage the user to answer first

## Language

Use English only for all questions, reference answers, headings, and feedback.
