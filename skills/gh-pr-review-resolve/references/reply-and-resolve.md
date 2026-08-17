# Reply And Resolve Review Threads

Use this reference immediately before posting a reply or resolving a live GitHub thread.

## Safe Sequence

1. Re-fetch unresolved threads immediately before acting.
2. Select the requested item from that live result and run a dry run.
3. Verify the requested thread's current code state, `threadId`, `latestCommentId`, path, line, URL, and exact reply body.
4. If the user has not explicitly approved that exact thread and reply body, show the dry run and ask them to reply with one numbered option:

   1. Post this reply and resolve the thread
   2. Revise the reply
   3. Cancel

   Option 1 is the required explicit approval. For option 2, ask for the replacement text, show the updated dry run, and request approval again.
5. Use `--thread-id` with `--expect-comment-id` for the approved live call.
6. Post the reply and resolve the thread.
7. Re-fetch and confirm the thread is absent from unresolved results; report the reply URL and resolved state.

The action is complete only after the live re-fetch confirms resolution. A thread that is still unresolved or needs a decision requires explicit user confirmation before closing.

## Commands

Dry-run a numbered item:

```bash
python3 <skill_dir>/scripts/reply_and_resolve_thread.py [PR] \
  --index <number> \
  --body '<markdown reply>' \
  --dry-run
```

Perform the verified action:

```bash
python3 <skill_dir>/scripts/reply_and_resolve_thread.py [PR] \
  --thread-id PRRT_xxx \
  --expect-comment-id 3394352828 \
  --body '<markdown reply>'
```

Use stdin for multiline Markdown replies. When handling multiple items, capture every `threadId` and `latestCommentId` first, then process them one at a time and re-fetch after each action. Live unresolved indexes can shift after any resolution or new review activity.
