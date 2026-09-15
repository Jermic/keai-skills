---
name: gh-pr-review
description: "Use when the user wants GitHub PR review-status overviews, analysis of existing review comments or a comment permalink, reply drafts, saved handling records, or authorized replies and thread resolution. Not a general code-review workflow for finding new issues in a diff."
---

# GH PR Review

One independently installable skill for PR overviews and existing review-comment handling. Infer the mode from the request, or honor an explicitly named mode. These are independent entry points, not a required pipeline. Mode names are instructions to the agent, not shell subcommands.

## Intent Routing

| Mode | User intent | Read only the matching reference |
| --- | --- | --- |
| `scan` | List PR review status across specified repositories. | [scan](references/scan.md) |
| `inspect` | Understand or classify comments on a PR or a specific comment. | [inspect](references/inspect.md), then [reporting](references/reporting.md) |
| `draft` | Generate or lightly polish replies for selected comments. | [reply style](references/reply-style.md); use [inspect](references/inspect.md) only for missing or stale evidence |
| `record` | Save or update an existing handling report. | [review record](references/review-record.md) |
| `reply` | Publish the selected replies with authorization. | [reply and resolve](references/reply-and-resolve.md) |
| `resolve` | Close selected review threads with authorization. | [reply and resolve](references/reply-and-resolve.md) |

A bare PR/comment input defaults to `inspect`. With no target, infer the current branch's PR; ask only if it cannot be determined. A cross-repository overview uses `scan`; a supplied PR or comment does not need a prior scan. Carry the exact comment permalink through every later mode. If multiple actions are explicitly requested, perform only those actions in the order their dependencies require.

## Language

- Follow the user's current language for interaction, analysis, and saved records; an explicit language request takes precedence. Keep each report's headings, labels, and prose consistent rather than showing bilingual labels by default.
- Draft replies in the target comment's language unless the user specifies otherwise. If the comment has no identifiable natural language, use the user's language. Preserve approved wording unless a rewrite or translation was requested.
- Provide translations only when requested, and identify their target language. Keep translations separate from the publishable reply.
- Keep code identifiers, stable data keys, paths, IDs, URLs, proper names, and quoted source text unchanged. Script output is evidence: localize display labels and explanatory text without altering counts, links, identities, or state meanings.

## Boundaries

- Analysis and drafting are read-only. Fix code only when requested; posting and closing each require authorization for that action and scope. Reuse an approved target and reply rather than asking again; material changes require renewed authorization.
- A PR input reads all unresolved review threads; a comment permalink reads only that comment and necessary parent context. Never silently expand the scope to discover a thread ID. Known thread IDs can be fetched directly.
- Output in chat by default. Save only on request; do not append a menu or save prompt at completion. A report, draft, saved record, posted reply, and closed thread are distinct results.
- Preserve existing item numbers and comment IDs when continuing a report or drafting from an approved record. Refresh remote state before mutation without renumbering the selected items.

## Scripts

Resolve `<skill_dir>` to this directory. The bundled Python scripts require authenticated `gh` for live GitHub operations. Keep shell commands at the relevant checkout when inferring a repository or PR.

- `scripts/open_pr_review_summary.py`: repository-level overview and counts.
- `scripts/fetch_unresolved_threads.py`: PR, comment, or known-thread inspection.
- `scripts/reply_and_resolve_thread.py`: combined reply and resolution; use only when both are authorized. Separate actions are described in the action reference.

The task ends when the requested mode's result is complete. Read-only work does not imply a transition to posting or closing. Verify changed executable behavior using the existing offline checks; see the inspect reference for commands.
