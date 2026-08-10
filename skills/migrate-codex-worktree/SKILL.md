---
name: migrate-codex-worktree
description: Print a safe command that repairs one Codex task after its worktree path changes.
disable-model-invocation: true
---

# Migrate Codex Worktree

1. Resolve `<skill_dir>` to this skill's directory and run the read-only discovery command from `/private/tmp` while Codex is open: `python3 <skill_dir>/scripts/migrate_thread_worktree.py --discover`.
2. Read `THREAD_ID`, `OLD_PATH`, and `NEW_PATH` from its JSON output. Report the discovery error and stop if it cannot identify exactly one moved worktree.
3. Shell-quote the script path and all three discovered values. Output one sentence telling the user to fully quit Codex before running exactly one copyable command:

```bash
python3 <skill_dir>/scripts/migrate_thread_worktree.py THREAD_ID OLD_PATH NEW_PATH
```

Run discovery only; do not run the migration command or modify `~/.codex`. Complete only when the response contains the shutdown instruction and one command with exactly the three discovered arguments.
