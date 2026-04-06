# Priority Execution Plan

## Objective

Move PR Knowledge Hub from a passive learning archive toward an active repetition-prevention workflow.

## Priority 1: Improve Related Learning Recommendations

### Current State

- Related learning suggestions already exist on the PR detail page.
- Ranking is better than a raw list, but user trust still depends on whether the recommendation feels justified.
- The strongest product value is not storing knowledge, but returning the right knowledge at the right review moment.

### Change

- Improve recommendation ranking with richer signals such as repository fit, category alignment, status, confidence, and recency.
- Return recommendation explanations from the API.
- Render those explanations in the PR detail experience.

### Expected Outcome

- Recommendations become easier to trust because the ranking reflects more than token overlap.
- Users can understand why a suggestion surfaced without reading multiple old PRs first.
- The product shifts from "knowledge was saved" to "knowledge prevented repetition."

### Implementation Scope

- Backend scoring improvements in `api/app/services/pull_requests.py`
- Related recommendation response fields in `api/app/routers/pull_requests.py`
- Review comment and file path context in related recommendation matching
- PR detail rendering in `web/src/app/pull-requests/[id]/page.tsx`
- Type alignment in `web/src/lib/api.ts`
- Targeted regression and ranking tests in `api/tests/`

### Review And Test Standard

- Ranking behavior must be covered by explicit test cases.
- Response changes must preserve existing fields and add explanation metadata safely.
- UI must render recommendation reasons without breaking the existing PR detail flow.
- Backend tests and frontend build must pass before closing the task.

## Priority 2: Split AI Work Into Explicit Roles

### Current State

- Extraction and recommendation exist, but improvement work still concentrates in a small number of broad stages.

### Change

- Split extraction, normalization, consolidation, and recommendation into clearer AI or service roles.

### Expected Outcome

- Failures become easier to isolate.
- Quality tuning becomes more targeted and less risky.

## Priority 3: Measure Reuse And Impact

### Current State

- The system supports learning activation, but it does not yet prove whether repeated review issues are decreasing.

### Change

- Track reuse of learning items and the drop in similar review feedback after adoption.

### Expected Outcome

- Teams can evaluate the product by outcome, not just activity.
- Adoption conversations can rely on evidence instead of intuition.

## Execution Order

1. Finish Priority 1 end-to-end with implementation, review, and test evidence.
2. Validate recommendation quality against real PR data.
3. Move to Priority 2 once the recommendation surface is stable.
4. Add Priority 3 after reuse signals are available in production flows.
