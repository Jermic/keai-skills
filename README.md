# keai-skills

An Agent Skills repository for reusable workflows, scripts, and prompt conventions.

中文说明见 [README.zh.md](./README.zh.md).

## Prerequisites

- Node.js / npx installed.
- If this repository is private, the current environment must have access to `github.com:<github-owner>/keai-skills`.

## Installation

### Quick install

```bash
npx skills add <github-owner>/keai-skills
```

The command installs skills from the repository's `skills/<skill-name>/SKILL.md` layout.

### Available after install

Available skill names after installation:

```text
gh-pr-review
gh-local-cleanup
gh-release-prepare
list-worktrees
migrate-codex-worktree
notion-sync-markdown
zlibrary
```

### Update

To update, rerun the install command or use the update/reinstall command provided by your local `skills` CLI.

## Structure

```text
keai-skills/
├── README.md
├── README.zh.md
├── docs/
│   └── creating-skills.md
└── skills/
    ├── gh-pr-review/
    ├── gh-local-cleanup/
    ├── gh-release-prepare/
    ├── list-worktrees/
    ├── migrate-codex-worktree/
    ├── notion-sync-markdown/
    └── zlibrary/
```

- `skills/`: each child directory is one standalone skill and must contain `SKILL.md`.
- `docs/`: maintenance rules, new skill conventions, and future release notes if needed.
- `scripts/`: only add repository-level scripts when needed; each skill currently keeps its own `scripts/`.

## Skills

| Skill | Purpose | When to use | Install single skill |
| --- | --- | --- | --- |
| `gh-pr-review` | PR review overview, comment analysis, reply drafts, and authorized actions. | Infer intent or specify scan / inspect / draft / record / reply / resolve. | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review` |
| `gh-local-cleanup` | Audit local branches and worktrees against GitHub state. | Use when you want categorized cleanup candidates before removing local review checkouts, merged branches, or finished worktrees. | `npx skills add <github-owner>/keai-skills/skills/gh-local-cleanup` |
| `gh-release-prepare` | Prepare separate feature and version-bump release PRs. | Prepare separate feature and version-bump release PRs. | `npx skills add <github-owner>/keai-skills/skills/gh-release-prepare` |
| `list-worktrees` | List worktrees and their local and remote status. | List worktrees and their local and remote status. | `npx skills add <github-owner>/keai-skills/skills/list-worktrees` |
| `migrate-codex-worktree` | Print a repair command after a Codex worktree moves. | Print a repair command after a Codex worktree moves. | `npx skills add <github-owner>/keai-skills/skills/migrate-codex-worktree` |
| `notion-sync-markdown` | Sync local Markdown into an existing Notion page with minimal block replacements. | Use when local Markdown is the source of truth and unchanged Notion blocks and discussions should be preserved. | `npx skills add <github-owner>/keai-skills/skills/notion-sync-markdown` |
| `zlibrary` | Work with Z-Library books through the bundled `Zlibrary.py`. | Use when you want to search candidate books, inspect details, download selected books, check account limits, or extend Z-Library API usage. | `npx skills add <github-owner>/keai-skills/skills/zlibrary` |

## GitHub PR Review Workflow

`gh-pr-review` infers intent or accepts an explicit `scan / inspect / draft / record / reply / resolve` mode. Modes are independent entry points, not a mandatory pipeline. PR links read all unresolved threads; comment links read only the target and necessary parent context. Drafts follow the concise, outcome-first [reply style](skills/gh-pr-review/references/reply-style.md), grounded in final code.

Results stay in chat by default; saving and remote actions follow the request. [Record format](skills/gh-pr-review/references/review-record.md) and [judgments/statuses](skills/gh-pr-review/references/reporting.md) each have one source of truth.

### Migrating Old Names

`gh-pr-review-scan` and `gh-pr-review-resolve` are merged into `gh-pr-review`; the repository no longer provides the old entry points. Install the new skill, preserve any local customizations, then remove the two old installations through their original installation mechanism to avoid duplicate triggers. Use `gh-pr-review scan` for overviews, `inspect` for comment analysis, `draft` for replies, and `resolve` only for closing threads. These are agent mode instructions, not script subcommands.

## Maintenance

- Keep the skill directory name and the `name` field in `SKILL.md` frontmatter in sync.
- Use lowercase letters, numbers, and hyphens for skill names.
- Keep `description` focused on trigger scenarios instead of placing the full workflow in frontmatter.
- For skills with scripts, put scripts in that skill's own `scripts/` directory.
- After updating a local skill installation, sync it back into this repository under `skills/`.

See [docs/creating-skills.md](./docs/creating-skills.md) for maintenance rules.
