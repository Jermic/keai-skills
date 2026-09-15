---
name: list-worktrees
description: "Use when the user asks to list Git worktree status for the current project's registered worktrees, a specified project or path, or every worktree under an agent-managed root such as Codex or Claude."
---

# List Worktrees

1. Use the requested project, path, or agent-managed root. If none is specified and cwd is a Git checkout, default to that project's registered worktrees. Ask for scope only when no current project or explicit target can be determined; reuse the scope already selected in this task.
2. Resolve `<skill_dir>` to this skill's directory and run exactly one read-only scan:

```bash
python3 <skill_dir>/scripts/scan_worktrees.py --project .
python3 <skill_dir>/scripts/scan_worktrees.py --project <path> [<path> ...]
python3 <skill_dir>/scripts/scan_worktrees.py --agent-root <path> [<path> ...]
```

Use `--project` to include every worktree registered to each specified repository. Use `--agent-root` to include only Git worktrees found beneath each specified directory. The scan is complete when the command exits successfully and every discovered worktree appears exactly once in stable order.

3. Return the generated table, adapting only local-link syntax to the host renderer when necessary. Output only the Markdown table, including for an invalid path or an empty scope. Add no introduction, summary, recommendation, or follow-up text. Complete the response when it contains exactly that one table.

Keep the columns exactly `序号 | 项目名 | 分支 | HEAD | PR | 工作区 | 远端情况 | Worktree`. Preserve continuous numbering, branch or detached HEAD details, staged/unstaged/untracked counts, and the script's remote-verification wording. Treat cached tracking refs marked `非实时` only as fallback evidence.

Column specifics:
- `分支` and `HEAD` are separate columns; detached checkouts show `detached` in `分支`.
- `PR` lists matching GitHub pull requests for the checked-out branch as `[#N](https://github.com/…) STATE` (OPEN / DRAFT / MERGED / CLOSED), multiple PRs joined by `；`. Requires the `gh` CLI authenticated against a GitHub `origin`; when unavailable the cell shows `—`. This lookup is best-effort and read-only — never fail the scan over it.
- `Worktree` renders as a Markdown link `[目录名](</绝对路径>)`, with only the directory name as its label. Adapt the link syntax if the host requires another format; preserve the exact target path.
- Directories that are not Git worktrees are appended as `—` rows rather than aborting the scan.

Keep the scan read-only with optional Git locks disabled. Run no fetch, prune, checkout, switch, cleanup, or Git metadata write.
