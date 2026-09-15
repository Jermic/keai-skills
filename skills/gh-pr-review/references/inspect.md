# Inspect Review Comments

Resolve `<skill_dir>` to the parent skill directory. A PR URL, `owner/repo#123`, `#123`, number, or inferred current PR selects all unresolved review threads. A `#discussion_r<ID>` or `#issuecomment-<ID>` permalink selects only that comment and its parent when it is a reply. Never discard an anchor or expand a comment request into a PR scan; unsupported anchors must be reported.

When the target is omitted, use the canonical PR URL returned by `gh pr view` to identify the repository and number, including for fork PRs. Bare numbers and `#123` remain relative to `origin`; use a full PR URL for an explicit upstream target.

Run the matching fetch command and inspect the relevant current code. A comment result has limited context; do not claim to have read sibling replies or verified resolution state. A PR report requires the full paginated result. Unresolved threads with more than 100 comments are completed through the existing single-thread pagination route; incomplete or duplicate results fail instead of being reported as complete. Reuse already fetched evidence while it remains relevant; refresh the selected target when code or comments changed or an action needs live validation.

For an analysis report, use [reporting.md](reporting.md). For requested reply drafts, use [reply-style.md](reply-style.md); drafting does not require reprinting the entire analysis report.

## Commands

Resolve `<skill_dir>` to this skill's directory. Run from the target checkout when inferring a PR:

```bash
python3 <skill_dir>/scripts/fetch_unresolved_threads.py [PR-or-comment-URL]
python3 <skill_dir>/scripts/fetch_unresolved_threads.py 'https://github.com/owner/repo/pull/35#discussion_r123'
python3 <skill_dir>/scripts/fetch_unresolved_threads.py owner/repo#35 --thread-id PRRT_xxx
```

The PR result includes metadata and `unresolvedThreads` sorted newest-first by `latestCommentAt`, with `commentCount` and `latestComment`. A known thread ID fetches that thread directly, including its resolved state. A comment result includes `comment`, optional `parentComment`, and an explicit context limit; it is not a whole-thread report. Numeric comment IDs and thread IDs are different identifiers.

GitHub's comment API does not directly return a review thread ID. If only a comment permalink is available, inspect it directly. To resolve it, use an already known and verified thread ID, or the exact thread's browser UI when available and authorized. Never enumerate the PR to discover the thread ID for a comment-only request; report the limitation if neither route is available. Conversation comments (`issuecomment-`) are not resolvable review threads.

Inspection is complete when every selected item is reported with its evidence and context limits. Do not append an unrequested save or action prompt.

After changing fetching or reply logic, run the bundled offline checks:

```bash
python3 <skill_dir>/scripts/fetch_unresolved_threads.py --self-check
python3 <skill_dir>/scripts/check_review_scope.py
```
