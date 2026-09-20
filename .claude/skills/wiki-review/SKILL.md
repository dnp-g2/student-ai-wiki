---
name: wiki-review
description: Feynman-technique review mode for studying. This skill should be used when the user says "review", "quiz me", "test my understanding", or names a course/concept they want to study. Quizzes the user, adjusts confidence based on answers, and generates practice questions for weak concepts.
---

# Wiki Review: Feynman Review

Test understanding using the Feynman technique.

## Steps

1. Read `wiki/hot.md` and `wiki/index.md` to locate the target concepts
2. Find concepts with confidence:low/medium (prioritize weak concepts)
3. **Feynman questions**: Ask as a complete beginner; have the user explain in the simplest terms
   - Ask "why" and "what if", not "what is"
   - Keep probing until the user cannot answer to find the limits of understanding
4. **Assess answers**:
   - Correct and complete → increase confidence and update `last_reviewed`
   - Gaps in the answer → identify gaps, explain the correct understanding, and maintain or lower confidence
5. **Update pages**: Adjust the concept page's `confidence` and `last_reviewed` fields
6. **Generate practice questions**: For concepts still at low confidence, use exam-prep logic to write questions to `wiki/exam-prep/{course}.md`

## Feynman Question Examples

- ❌ "What is the attention mechanism?" (tests recall)
- ✅ "What happens if you remove the scaling factor √d_k before softmax? Why?" (tests understanding)
- ✅ "Use an everyday analogy to explain the roles of the Q, K, and V matrices." (tests internalization)

## Language

Use English only for questions and feedback.
