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
gh-pr-review-scan
gh-pr-review-resolve
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
    ├── gh-pr-review-scan/
    ├── gh-pr-review-resolve/
    └── zlibrary/
```

- `skills/`: each child directory is one standalone skill and must contain `SKILL.md`.
- `docs/`: maintenance rules, new skill conventions, and future release notes if needed.
- `scripts/`: only add repository-level scripts when needed; each skill currently keeps its own `scripts/`.

## Skills

| Skill | Purpose | When to use | Install single skill |
| --- | --- | --- | --- |
| `gh-pr-review-scan` | Scan review status across multiple repositories or PRs. | Use when you want to see which open/draft PRs still have review comments and resolved/unresolved thread counts. | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review-scan` |
| `gh-pr-review-resolve` | Handle unresolved review threads for one PR. | Use when you want to judge comments one by one, generate Reply/Reply_ZH, save review records, reply, and resolve threads. | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review-resolve` |
| `zlibrary` | Work with Z-Library books through the bundled `Zlibrary.py`. | Use when you want to search candidate books, inspect details, download selected books, check account limits, or extend Z-Library API usage. | `npx skills add <github-owner>/keai-skills/skills/zlibrary` |

## GitHub PR Review Workflow

1. Use `gh-pr-review-scan` first for an overview and to find PRs that need attention.
2. Use `gh-pr-review-resolve` for one PR to organize unresolved review threads.
3. If a review record is generated, save it in the current project by default:


```text
reviews/<owner>-<repo>-<pr-number>.md
```

Example:

```text
/reviews/keai-skills-1.md
```

Review records use this table format:

```md
| # | Status | ID | Link | Reply | Reply_ZH |
| --- | --- | --- | --- | --- | --- |
```

## Maintenance

- Keep the skill directory name and the `name` field in `SKILL.md` frontmatter in sync.
- Use lowercase letters, numbers, and hyphens for skill names.
- Keep `description` focused on trigger scenarios instead of placing the full workflow in frontmatter.
- For skills with scripts, put scripts in that skill's own `scripts/` directory.
- After updating a local skill installation, sync it back into this repository under `skills/`.

See [docs/creating-skills.md](./docs/creating-skills.md) for maintenance rules.
