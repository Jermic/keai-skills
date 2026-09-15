# Local Review Record

Use this reference only when the user requests a saved record. Read `reporting.md` for the handling judgments and current statuses; use the same values in chat and in the record.

## Format

The example below uses English for documentation. Render its heading, scope note, column labels, judgment/status labels, and explanatory prose consistently in the record language defined by the skill. Preserve identifiers and any publishable reply in its own target language. Use the stable codes and exact English/Chinese display labels from `reporting.md`; translate consistently for other languages. Do not create a separate set of status meanings for each language.

```md
PR #<number> review handling record.

Scope: <all unresolved threads in this PR, or the selected comment permalink>. Numbering follows this report.

| # | Judgment | Status | ID | Link | Summary | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Required | Addressed | 123 | [comment](https://github.com/owner/repo/pull/35#discussion_r123) | Fixed in the current commit; verification is recorded below. | Reply and resolve if authorized. |
```

`ID` is the numeric comment ID, not the GraphQL thread ID. When thread IDs are known, preserve them with the item so later actions need not rediscover them. For comment-only requests, record the fetched context limit and unknown remote resolution state.

Include a `Reply` column only when replies were drafted. Add `Translation (<target language>)` only when a translation was requested, localizing the column labels to the record language. Keep the publishable reply and translation in separate cells and do not create empty columns. When updating an existing record, preserve its content and apply these conventions only to the requested changes; translating older content requires a translation request.

## Saving

Save as `reviewcheck.md` in the current checkout unless the user supplies another path. Preserve an existing record by creating a timestamp-suffixed file for a separate report. Update or replace an existing record only when requested; an explicit update request does not require another confirmation.

The record is complete when it contains exactly the selected items, their judgments and statuses, and any requested replies, without claiming to cover unselected comments.
