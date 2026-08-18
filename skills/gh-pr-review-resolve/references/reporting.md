# Reporting Unresolved Review Threads

## Output

Classify every fetched thread exactly once as **Fixed by current commit/diff**, **Still unresolved**, or **Needs decision**.

Number threads by the live newest-first `latestCommentAt` order. For each item include priority, classification, `file:line`, reviewer, latest comment date, comment link, the explicit comment ID as `Comment ID: <latestComment.databaseId>` on its own line, summary, and the next action.

List fixed threads with suggested replies first, then still-unresolved and needs-decision threads by priority. When recency matters, summarize the whole thread while using its latest comment to determine ordering.

The reporting branch is complete when every fetched unresolved thread appears once with a classification and every still-unresolved or needs-decision thread has a priority.

## Priority

- **High**: correctness bugs, data loss, runtime errors, broken user flows, security or privacy exposure, invalid persisted state.
- **Medium**: maintainability risks that threaten future correctness, brittle contracts, confusing ownership, missing defensive handling.
- **Low**: naming, documentation, formatting, and local readability issues.

## Reply Style

Draft a concise implementation note that states the concrete change and why it addresses the concern. Put only the copy-ready English reply in a fenced `md` block.

Use a natural status word such as `Resolved.`, `Updated.`, `Fixed.`, `Noted.`, `Removed.`, or `Improved.` when it adds information. For an outdated thread that is fixed, mention the replacement mechanism. For a thread that remains unresolved, state the remaining issue instead of drafting a completed-fix reply.

Example:

```md
Updated. <specific code-level change and why it addresses the review concern>.
```
