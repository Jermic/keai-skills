---
name: gh-pr-review-scan
description: "Use when the user wants a GitHub PR review scan across repositories, including open or draft PRs and resolved or unresolved review counts."
---

# GitHub PR Review Scan

## Overview

Query GitHub with `gh` and produce a Markdown table of PRs authored by the current authenticated user. Default to open PRs; label open drafts as `DRAFT`.

This skill remains PR-level and works independently. For thread-level handling inside one PR, switch to `gh-pr-review-resolve` when it is installed. If it is unavailable, return the scan only and offer:

```bash
npx skills add Jermic/keai-skills/skills/gh-pr-review-resolve
```

## Quick Start

Resolve `<skill_dir>` to the directory containing this `SKILL.md`, then run the bundled script from any checkout:

```bash
python3 <skill_dir>/scripts/open_pr_review_summary.py <owner>/<repo-a> <owner>/<repo-b> <owner>/<repo-c>
```

The script outputs a Markdown table with clickable repo and PR links:

```markdown
| Repo | PR | Status | Title | Comment Total | Resolved | Unresolved |
```

## Counting Rules

- `Comment Total` is `PR conversation comments + review thread comments`.
- `Resolved` is the number of review threads where `isResolved == true`.
- `Unresolved` is the number of review threads where `isResolved == false`.
- Closed and merged PRs are excluded by default through `state:open`.
- Draft PRs are included and displayed as `DRAFT`.
- Repositories with no matching PRs are shown with a `No open/draft PR` row.

## Workflow

1. Run the bundled script with every requested repository. This step is complete when every repository has a result row and the script exits successfully.
2. Return the generated table directly, preserving Markdown links. The scan is complete when every matching PR has status and comment counts, including all paginated review threads.
3. If `gh` authentication or network access fails, report that failure instead of presenting a partial table as complete.

## Options

Pass `--all-states` before repositories to include closed and merged PRs too:

```bash
python3 <skill_dir>/scripts/open_pr_review_summary.py --all-states <owner>/<repo>
```

Pass `--author <login>` to query a specific author instead of the current `gh` user:

```bash
python3 <skill_dir>/scripts/open_pr_review_summary.py --author <github-login> <owner>/<repo>
```
