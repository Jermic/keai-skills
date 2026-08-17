---
name: list-worktrees
description: "Use when the user asks to list Git worktree status for the current project's registered worktrees, a specified project or path, or every worktree under an agent-managed root such as Codex or Claude."
---

# List Worktrees

1. Determine the scan scope. If the user has not chosen one, ask them to reply with one numbered option:

   1. Current project's registered worktrees (recommended)
   2. A specified project or path
   3. Every worktree under an agent-managed root

   Ask for a path only after the user chooses option 2 or 3 and the exact path is not known. Continue only when one scope is explicit.
2. Resolve `<skill_dir>` to this skill's directory and run exactly one read-only scan:

```bash
python3 <skill_dir>/scripts/scan_worktrees.py --project .
python3 <skill_dir>/scripts/scan_worktrees.py --project <path> [<path> ...]
python3 <skill_dir>/scripts/scan_worktrees.py --agent-root <path> [<path> ...]
```

Use `--project` to include every worktree registered to each specified repository. Use `--agent-root` to include only Git worktrees found beneath each specified directory. The scan is complete when the command exits successfully and every discovered worktree appears exactly once in stable order.

3. Return the command's stdout verbatim. Output only the Markdown table, including for an invalid path or an empty scope. Add no introduction, summary, recommendation, or follow-up text. Complete the response when it contains exactly that one table.

Keep the columns exactly `序号 | 项目名 | Worktree | 分支 / HEAD | 工作区 | 远端情况`. Preserve continuous numbering, branch or detached HEAD details, staged/unstaged/untracked counts, and the script's remote-verification wording. Treat cached tracking refs marked `非实时` only as fallback evidence.

Keep the scan read-only with optional Git locks disabled. Run no fetch, prune, checkout, switch, cleanup, or Git metadata write.
