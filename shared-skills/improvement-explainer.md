---
name: improvement-explainer
description: Explain implementation work in terms of what should improve, why it matters, and what actions will produce that improvement. Use when planning or presenting features, refactors, debugging, or architecture changes and you need to describe "what problem this improves", "what will be changed", "why this approach was chosen", and "how to communicate the expected outcome" in clear Japanese or English.
---

# Improvement Explainer

Describe work as an improvement loop, not as a feature list.

## Core Frame

Always organize the explanation in this order:

1. Current friction
2. Desired improvement
3. Proposed change
4. Why this change is the right lever
5. Expected effect
6. Tradeoffs or limits

Use this frame even when the user only asks for a summary. Compress it if needed, but keep the causal flow.

## Default Questions To Answer

Before writing, infer or extract these points:

- What is currently painful, slow, risky, unclear, or expensive?
- Who feels that pain?
- What behavior should improve after the change?
- What concrete action or implementation causes that improvement?
- Why this approach instead of simpler or more obvious alternatives?
- What will remain unsolved?

If any point is unknown, state the assumption instead of faking certainty.

## Output Pattern

Use wording close to this:

- `problem`: the current problem or friction
- `change`: the concrete implementation or process change
- `mechanism`: the causal link between the action and the expected improvement
- `expected effect`: what becomes faster, clearer, safer, cheaper, or easier
- `remaining gap`: what this does not solve yet

When the audience is technical, keep the cause-and-effect precise.  
When the audience is mixed, prefer simpler wording over implementation detail.

## Writing Rules

- Start from the problem, not the tool.
- Do not say only "add X" or "use Y"; explain what gets better.
- Avoid vague claims like "UX improves" or "maintainability improves" without mechanism.
- Tie every major change to one intended improvement.
- Separate current pain from future vision.
- If multiple changes exist, group them by improvement goal.

## Good Compression Pattern

For short explanations, use 3 lines:

1. `current problem`
2. `what to change`
3. `how it improves`

Example:

```text
PR review lessons currently disappear and are hard to reuse in the next change.
So extract structured learnings from review comments and fix history, then save them in a weekly note.
This turns one-off review feedback into knowledge that can be reused in the next implementation.
```

## Stronger Pattern For Plans Or LT Prep

When the user is planning a project, architecture, or talk, use this expanded shape:

### 1. Improvement Goal
- Define what should get better

### 2. Why It Matters
- Explain why this problem is worth solving now

### 3. Chosen Change
- Describe the implementation, design, or workflow change

### 4. Why This Approach
- Compare briefly with rejected alternatives if relevant

### 5. Expected Outcome
- Describe concrete improvement in behavior or decision quality

### 6. Remaining Gaps
- State what still needs iteration

## Anti-Patterns

Do not:

- list technologies without linking them to an improvement goal
- describe implementation steps without saying what they fix
- describe abstract ideals without concrete actions
- overstate certainty when the effect is still hypothetical
- present "AI will solve it" as the explanation

## Preferred Tone

- clear
- causal
- neutral
- pragmatic

Prefer `A is the problem, so do B, which improves C.` over decorative language.
