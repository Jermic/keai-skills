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
- Keep each skill self-contained. Avoid shared code until duplication is painful.

## Naming

- Use lowercase letters, numbers, and hyphens only.
- Keep the directory name equal to the `name` field in `SKILL.md`.
- Prefer names that describe the user action, such as `gh-pr-review-scan` or `gh-pr-review-resolve`.

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

In `SKILL.md`, prefer relative script paths such as:

```text
scripts/example.py
```

Use absolute paths only when the skill is installed locally and the path is intentionally fixed.

Prefer Python for skill scripts in this repository. Keep shell scripts only for thin wrappers around a Python entry point or for unavoidable platform glue.

## Review Record Convention

GitHub PR review handling records use this path:

```text
reviews/<owner>-<repo>-<pr-number>.md
```

The table format is:

```md
| # | Status | ID | Link | Reply | Reply_ZH |
| --- | --- | --- | --- | --- | --- |
```

Status values:

- `待处理`
- `处理中`
- `已解决`
- `已回复`
- `已关闭`
- `无需处理`
- `需确认`
- `暂缓`

## Syncing Installed Skills

When a locally installed skill changes, sync the full directory into this repository:

```bash
cp -R ~/.codex/skills/<skill-name> skills/
cp -R ~/.agents/skills/<skill-name> skills/
```

After syncing, check for stale names:

```bash
rg "old-skill-name" skills/
```
