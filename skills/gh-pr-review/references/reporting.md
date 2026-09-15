# Reporting Review Comments

## Scope and Ordering

Report each selected item exactly once. A PR input covers all fetched unresolved threads; a comment permalink covers only that comment and its fetched parent context. Preserve the fetch order and assign stable numbers within this report. Do not regroup items after numbering.

For each item include the handling judgment, current status, priority, comment link and numeric ID, author, date, relevant `file:line` when available, evidence, and the smallest next action. Missing thread context or resolution state must be stated as unknown, not inferred from a comment's position or wording.

## Handling Judgment

Choose one judgment for each item. The codes below are stable identifiers. For English or Chinese reports, use the exact display labels below unless the user requests different wording; show only the report language, not bilingual pairs or internal codes. For other languages, translate each meaning consistently. Use the same labels in chat and saved records. These definitions are self-contained and do not require any external AGENTS.md:

| Code | English | Chinese | Use when | Smallest next action |
| --- | --- | --- | --- | --- |
| `must_fix` | Required | 必须修复 | Evidence shows a correctness, security, data-loss, or explicit requirement violation. | Describe the concrete fix and its narrow verification. |
| `improve` | Suggested | 建议改进 | The suggestion has a real maintainability or usability benefit but is not a correctness blocker. | Explain the benefit and cost; keep it optional unless requested. |
| `discuss` | Discuss | 需要讨论 | Product intent, requirements, or an architectural tradeoff is genuinely undecided. | State the specific decision and its alternatives. |
| `outdated` | Outdated | 已过时 | The concern applied to an earlier revision and current code removes it. | Cite the current code or commit that supersedes it. |
| `no_action` | Dismissed | 无需处理 | The premise is incorrect, the behavior is intentional, or the comment duplicates another tracked item. | Explain the evidence or link the duplicate; do not dismiss without evidence. |

GitHub's `isOutdated` flag alone does not prove the concern is fixed. When evidence is insufficient, say what remains unverified rather than assigning a confident verdict. Priority is separate: High for correctness/security/data-loss and broken user flows; Medium for material maintainability or usability risk; Low for local naming, documentation, and presentation improvements.

## Current Status

Status records progress, not whether the reviewer is right. Use these stable codes and localize their display labels in the same way as judgments:

| Code | English | Chinese | Meaning |
| --- | --- | --- | --- |
| `not_started` | Pending | 未处理 | No handling action taken yet. |
| `in_progress` | In progress | 进行中 | Investigation or an authorized change is underway. |
| `fixed` | Addressed | 已处理 | The agreed handling is complete, through a verified change or an evidence-backed explanation prepared for the item. Classification alone is insufficient. For changes, state whether they are local, committed, or pushed and what was verified. This does not imply that a reply was posted or the GitHub thread was resolved. |
| `replied` | Replied | 已回复 | A reply was posted, but closure is not verified. |
| `resolved` | Resolved | 已关闭 | GitHub confirms the review thread is resolved. |
| `deferred` | Deferred | 暂缓 | The user explicitly deferred this item. |

The `no_action` and `outdated` judgments can coexist with an open thread. An unknown remote state is reported separately; do not invent a status of `resolved`. Classifying a comment does not authorize implementation or external actions.

For requested reply drafts, use [reply-style.md](reply-style.md). Keep analysis metadata outside the publishable reply.

The report is complete when each selected item has an evidence-backed judgment or an explicit evidence gap, a current status, priority, and a concrete next action where needed.
