# Reply And Resolve Review Threads

Use this reference only for requested posting or thread resolution. Reading, classifying, and drafting alone do not authorize either action.

## Sequence

1. Use the already inspected target, current code evidence, exact reply body, `threadId`, and `latestCommentId`. If posting and resolution have not been authorized for this scope, present the concrete reply and target once and request the missing authorization. Reuse an approved batch; ask again only if the target, content, or action materially changes.
2. Execute by stable `--thread-id` with `--expect-comment-id`. The script fetches only this thread, checks PR ownership, linked-comment membership when applicable, and latest comment identity before any write. No separate fetch or dry run is required immediately before it. `--dry-run` remains available only for an explicitly requested preview or troubleshooting.
3. The script posts via `addPullRequestReviewThreadReply` using the verified thread ID (the latest comment ID is only a freshness guard), resolves the thread, and re-fetches that same thread to verify resolution. Report its reply URL and verified state; do not run an extra whole-PR scan afterward.

For comment permalinks without a known thread ID, use the exact thread's browser UI when available and authorized; otherwise report that resolution needs a thread ID. Never fall back to scanning all PR threads. Ordinary conversation comments cannot be resolved as review threads.

## Command

```bash
python3 <skill_dir>/scripts/reply_and_resolve_thread.py [PR-or-comment-URL] \
  --thread-id PRRT_xxx \
  --expect-comment-id 123 \
  --body-file reply.md
```

Use `--body-file` or stdin for multiline Markdown. `--index` is a legacy PR-wide selector and must not be used for comment-only requests; prefer the stable IDs already returned by inspection.

This command performs both posting and resolution; use it only when both are authorized. For resolution-only requests or recovery after a posted reply, call `resolveReviewThread` on the verified thread ID without posting again, then fetch only that thread to verify. For reply-only requests, post only the authorized reply through the appropriate GitHub endpoint or exact browser target and verify the returned comment.

If posting succeeds but resolution fails, preserve the reported reply URL and retry resolution only. If a posting response is uncertain, inspect the same thread before retrying to avoid duplicate replies. A changed latest comment aborts the script: inspect the new activity and re-evaluate the action before retrying.
