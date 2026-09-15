# PR Reply Style

Read when generating or polishing PR comment replies, not for a status scan or classification-only report.

## Evidence Before Wording

Use the selected comment, confirmed handling decision, and final relevant code. Reuse adequate evidence already in the task; inspect only what is missing or stale. Verify any claimed fix before drafting, even if the reply will be one word. Do not present proposed, reverted, or unverified changes as implemented. If a decision is missing, flag the exact uncertainty for the user rather than promising a change.

Preserve the user's edited or approved wording. Apply only requested polishing; do not replace their structure or tone with a new explanation.

## Writing Rules

- Be direct and factual. Lead with the result and add only information the reviewer does not already have. Avoid tentative openings such as “If you mean…”.
- Match length to substance. A fully addressed small issue can use `Fixed.`, `Removed.`, or `Inlined.` alone. Explain more only for behavior, correctness, or a disagreement; do not pad every reply to a fixed sentence count.
- For partial adoption, name exactly what changed and what remains unchanged or outside this PR. Do not describe the entire concern as fixed.
- When retaining behavior, briefly state its purpose or reason. Omit intermediate attempts and abandoned approaches.
- For outdated comments, explain that the referenced implementation no longer exists without implying it was removed by the latest change. Verify this against code; the GitHub outdated flag alone is insufficient.
- Distinguish behavior changes from structural cleanup. Retain function or field names only when they clarify the result; avoid retelling the implementation.

## Draft Presentation

Keep the user's review context outside the publishable reply: item number, comment ID/link, and any necessary evidence or unresolved decision. Preserve existing numbering. Put the copy-ready reply in a fenced `md` block, using the language policy in the skill entrypoint. Add a separately labeled translation only when requested; translations and internal classifications are not part of the posted reply. Saved records follow the record reference's column convention.

Generate drafts without modifying code, posting, or resolving unless those actions are separately authorized. Approval of wording alone does not authorize publication. Use the action reference only when sending or closing was requested.

## Examples

Fully addressed small issue:

> Fixed.

Partial removal:

> Removed the redundant outer check. The internal guard remains.

Retained implementation:

> Kept `familyState` to avoid repeating the child count and pregnancy checks.

Outdated implementation with an unimplemented suggestion:

> The referenced implementation has since been removed. Versioning is not included in this PR.

These English examples illustrate scope and length, not a required output language or facts to reuse without verification. Apply the same brevity and precision in the chosen reply language. A draft is complete when each selected comment has a traceable reply or a clearly identified unresolved decision, with no unverified completion claims.
