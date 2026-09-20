---
name: wiki-review
description: Feynman-technique review mode for studying. This skill should be used when the user says "review", "quiz me", "test my understanding", or names a course/concept they want to study. Quizzes the user, adjusts confidence based on answers, and generates practice questions for weak concepts.
---

# Wiki Review: Feynman Review

Test understanding using the Feynman technique.

## Steps

1. Read wiki/hot.md and wiki/index.md to locate the target concepts
2. Find concepts with confidence:low/medium (prioritize weak concepts)
3. Ask Feynman questions: ask "why" and "what if", not "what is"
4. Keep probing until the user cannot answer to find the limits of understanding
5. Assess answers and update confidence and last_reviewed
6. Generate practice questions for concepts still at low confidence in wiki/exam-prep/{course}.md

## Feynman Question Examples

- ❌ "What is the attention mechanism?" (tests recall)
- ✅ "What happens if you remove the scaling factor √d_k before softmax?" (tests understanding)
- ✅ "Use an everyday analogy to explain the roles of the Q, K, and V matrices." (tests internalization)

Use English only for questions and feedback.
