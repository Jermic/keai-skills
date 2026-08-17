---
name: gh-pr-review-resolve
description: "Use when the user wants to handle one GitHub PR's review threads: inspect unresolved comments, classify fixes, draft replies, save review notes, or reply and resolve threads."
---

# GH PR Review Resolve

Handle unresolved review threads for one PR with thread-aware GitHub GraphQL data. This skill works independently. For a cross-repository dashboard, switch to `gh-pr-review-scan` when installed; otherwise keep the work scoped to one PR and offer:

```bash
npx skills add Jermic/keai-skills/skills/gh-pr-review-scan
```

## Workflow

1. Resolve the PR from a URL, `owner/repo#123`, `#123`, a number, or the current branch. This step is complete when `owner`, repository, and PR number are explicit.
2. Fetch live unresolved threads with `scripts/fetch_unresolved_threads.py`. This step is complete only when the script exits successfully; pagination or truncation errors mean the result is incomplete.
3. Complete only the requested branch using the matching reference below. If the request does not identify one branch, ask the user to reply with one numbered option:

   1. Summarize or prioritize comments and draft replies (recommended)
   2. Create or save a local review record
   3. Reply to and resolve selected threads

   The run is complete when the selected branch's completion criterion is satisfied.

## Branch References

| User intent | Required reference |
| --- | --- |
| Summarize or prioritize unresolved comments; draft replies | Inspect the current diff for every referenced path, then classify every fetched thread using `references/reporting.md`. |
| Create or save `reviewcheck.md` or another local handling record | Inspect the current diff for every referenced path, then assign every fetched thread a status from `references/review-record.md`. |
| Reply to and resolve known threads | Read `references/reply-and-resolve.md`; verify only the requested live threads unless the user also asks for a full review. |

## Fetch Script

Resolve `<skill_dir>` to the directory containing this `SKILL.md`, then run from the target checkout:

```bash
python3 <skill_dir>/scripts/fetch_unresolved_threads.py [PR]
```

Accepted PR forms:

```bash
python3 <skill_dir>/scripts/fetch_unresolved_threads.py https://github.com/<owner>/<repo>/pull/35
python3 <skill_dir>/scripts/fetch_unresolved_threads.py <owner>/<repo>#35
python3 <skill_dir>/scripts/fetch_unresolved_threads.py 35
python3 <skill_dir>/scripts/fetch_unresolved_threads.py
```

The JSON output contains PR metadata and complete unresolved threads sorted newest-first by `latestCommentAt`. Each thread includes `commentCount`, `latestCommentAt`, and `latestComment`.

Run the bundled parser check after changing the fetch script:

```bash
python3 <skill_dir>/scripts/fetch_unresolved_threads.py --self-check
```
