---
name: gh-local-cleanup
description: "Audit local Git branches and worktrees against GitHub PR and remote state. Use when the user wants to inspect stale checkouts, classify safe cleanup candidates, remove review-only branches, or clean finished worktrees across one or more repositories."
---

# GH Local Cleanup

Build an evidence chain before deleting local Git state. Scan first, present every item by category, and execute only the categories the user confirms.

## Scan

Resolve `<skill_dir>` to this skill's directory, then run from any location:

```bash
python3 <skill_dir>/scripts/scan_local_git.py <repo-path> [<repo-path> ...]
```

The script refreshes `origin` with `git fetch --prune`, reads every local branch and worktree, and queries GitHub PRs with authenticated `gh`. Pass `--no-fetch` only when the user explicitly wants cached remote state.

The scan is complete when every local branch and worktree appears exactly once under one of these categories:

| Category | Meaning |
| --- | --- |
| `DELETE` | Local state is redundant: merged, fully represented by the remote, or a review-only checkout owned by another PR author |
| `CONFIRM` | Deletion preserves remote data but needs intent confirmation, or requires switching/removing a worktree first |
| `KEEP` | Active, default, backup, divergent, or locally unique state |
| `BLOCKED` | A dirty worktree prevents safe cleanup |

Preserve the user's language when presenting the generated tables. Call out current branches, dirty worktrees, local-only commits, open PRs, and remote-deleted branches explicitly.

## Confirm

Show the branch and worktree tables before changing Git state. State whether the proposed action removes a worktree, a local branch, or both. Treat remote branch deletion as a separate action outside this skill's default scope.

After the tables, ask the user to reply with one numbered option, omitting any option that has no eligible items:

1. Remove every `DELETE` candidate (recommended)
2. Choose specific `DELETE` or `CONFIRM` items
3. Cancel cleanup

If the user chooses option 2, present every eligible item as a numbered list, including its category and whether the action removes a worktree, a local branch, or both, then ask them to reply with the item numbers. The confirmation step is complete only when the user has selected an exact category or exact numbered items to remove.

## Clean

Re-check each selected worktree with `git status --porcelain` immediately before removal. Use `git worktree remove <path>` for clean secondary worktrees.

Delete confirmed local branches with `git branch -d`. Use `git branch -D` only when the scan proved one of these evidence chains and the user confirmed deletion:

- the PR is merged;
- the commit is contained in the refreshed default branch;
- the local tip exactly matches an existing remote branch;
- the commit is preserved by another named local or remote branch.

After cleanup, report `git status --short --branch`, the current branch, `git worktree list`, and the remaining local branches. The cleanup is complete when all selected items are absent and every preserved item remains reachable.
