---
name: wiki-diagram
description: Add Mermaid diagrams to wiki pages to aid understanding. This skill should be used during ingest/review when a concept involves a process, architecture, sequence, hierarchy, or comparison that is easier to grasp visually, or when the user explicitly asks to "diagram"/"visualize" a concept.
---

# Wiki Diagram: Mermaid Visualization

Add Mermaid diagrams to concept pages. Obsidian renders Mermaid code blocks natively; no plugin is required.

## When to Diagram

Add a diagram only when it explains the content better than prose, not on every page. Suitable cases:

- Multi-step processes/algorithms → flowchart
- Protocol interactions/attack steps with timing (suitable for COMP4337) → sequenceDiagram
- System architecture/model structure with component relationships → flowchart
- Concept classification/knowledge maps → mindmap
- State transitions/lifecycles → stateDiagram-v2
- Concept relationship networks (cross-course connections) → graph

Unsuitable cases: single definitions, purely mathematical derivations, or linear narratives with no branching or relationships.

## Diagram Type Mapping

| Content Type | Mermaid Type |
|---|---|
| Algorithm steps/data processing | `flowchart TD` |
| Protocol/attack interaction sequences | `sequenceDiagram` |
| Model architecture/system components | `flowchart LR` |
| Concept classification/knowledge maps | `mindmap` |
| State machines/lifecycles | `stateDiagram-v2` |
| Concept relationship networks | `graph TD` |

## Placement

Add a `## Diagram` section after `Intuition` or `Detailed` on the concept page. Insert it locally; do not rewrite the entire page.

```markdown
## Diagram

\`\`\`mermaid
flowchart TD
    A[Input] --> B[Process]
    B --> C[Output]
\`\`\`
```

## Quality Rules

1. **≤10 nodes**: Simplify larger diagrams or show only the core path
2. **English-only labels**: Use English for all node text, consistent with the rest of the page
3. **At most 1–2 diagrams per page**: Avoid visual clutter
4. **Valid syntax**: Check node IDs, arrows, and paired brackets/quotes to avoid rendering failures
5. For diagrams from slides, first describe key points on the source page, then decide whether Mermaid can express the logic more clearly (an exact reproduction is not required)

## Triggers

- **Automatic**: When ingest/review creates or updates concept pages, apply the criteria above (see wiki-ingest steps)
- **Manual**: When the user says "diagram this"/"visualize X" or uses `/diagram {concept}`, create or improve a diagram on the specified concept page
