# Creating And Maintaining Skills

This repository stores personal Agent Skills under `skills/`.

## Directory Layout

```text
skills/<skill-name>/
├── SKILL.md
├── scripts/
└── agents/
```

- `SKILL.md` is required.
- `scripts/` is optional and belongs to the skill that uses it.
- `agents/` is optional and stores helper agent prompts/config.
- Keep each skill independently installable: put its runtime scripts and required references inside its own directory. Do not require another skill, a prior scan, or an external AGENTS.md to define its workflow. Reuse helpers within a skill when useful.

## Naming

- Use lowercase letters, numbers, and hyphens only.
- Keep the directory name equal to the `name` field in `SKILL.md`.
- Prefer names that describe the user action, such as `gh-pr-review` or `list-worktrees`.

## Frontmatter

Use concise frontmatter:

```yaml
---
name: gh-pr-review-example
description: Use when the user asks for a specific, recognizable workflow trigger.
---
```

Description rules:

- Start with `Use when`.
- Describe trigger conditions, not the whole workflow.
- Keep it searchable with real words the user would say.

## Script Paths

When a script runs from the skill directory, prefer a relative path:

```text
scripts/example.py
```

When a script must run from another checkout, resolve `<skill_dir>` from the active `SKILL.md` and use `<skill_dir>/scripts/example.py`. Use a fixed absolute path only when the installation location is intentionally fixed.

Prefer Python for skill scripts in this repository. Keep shell scripts only for thin wrappers around a Python entry point or for unavoidable platform glue.

## Review Record Convention

The canonical record path and table live in `skills/gh-pr-review/references/review-record.md`; judgment and status definitions live in that skill's `references/reporting.md`. Keep installed copies self-contained and link to these sources from repository documentation instead of duplicating rules.

## Syncing Installed Skills

Choose one authoritative installed directory; `~/.codex/skills/<skill-name>` and `~/.agents/skills/<skill-name>` may be different versions or symlinks to the same directory. Compare that source with `skills/<skill-name>` before syncing, and preserve unrelated repository changes.

Copy only the intended additions and modifications. List files removed from the source and remove their repository counterparts only when those deletions are part of the authorized sync; overlay copying alone leaves stale files behind. Do not copy both installed directories in sequence or use an unreviewed destructive mirror. Exclude generated caches and task artifacts.

After syncing, inspect the scoped diff and check any renamed references. Run the skill's existing checks only for changed executable behavior or packaging that needs verification.
