# keai-skills

一个 Agent Skills 仓库，用来沉淀可复用的工作流、脚本和提示规范。当前重点是 GitHub PR review 处理。

## 前置要求

- 已安装 Node.js / npx。
- 如果仓库是私有仓库，当前环境需要有权限访问 `github.com:<github-owner>/keai-skills`。

## 安装

### 快速安装

```bash
npx skills add <github-owner>/keai-skills
```

这个命令会从 GitHub 拉取仓库，并按 `skills/<skill-name>/SKILL.md` 结构安装可用 skills。

### 安装后可用

安装后可以通过这些 skill 名触发：

```text
gh-pr-review-scan
gh-pr-review-resolve
zlibrary
```

### 更新

当本仓库有新版本后，重新运行：

```bash
npx skills add <github-owner>/keai-skills
```

如果你的本地 skills 工具支持更新命令，也可以使用它提供的 update/reinstall 方式。

## 目录结构

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

- `skills/`: 每个子目录是一个独立 skill，必须包含 `SKILL.md`。
- `docs/`: 维护规范、创建新 skill 的约定，以及未来可能加入的发布说明。
- `scripts/`: 只在需要仓库级脚本时添加；目前每个 skill 自带自己的 `scripts/`。

## 可用 Skills

| Skill | 作用 | 什么时候用 | 单独安装 |
| --- | --- | --- | --- |
| `gh-pr-review-scan` | 扫描多个仓库或多个 PR 的 review 状态 | 想知道哪些 open/draft PR 还有 review comments、resolved/unresolved thread 数量 | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review-scan` |
| `gh-pr-review-resolve` | 处理单个 PR 的 unresolved review threads | 想逐条判断评论是否已修、生成 Reply/Reply_ZH、保存 review 处理记录、回复并 resolve thread | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review-resolve` |
| `zlibrary` | 用内置 `Zlibrary.py` 处理 Z-Library 书籍 | 想搜索候选书、查看详情、下载选中的书、检查账号额度，或扩展 Z-Library API 能力 | `npx skills add <github-owner>/keai-skills/skills/zlibrary` |

## GitHub PR Review 工作流

1. 先用 `gh-pr-review-scan` 看总览，找出需要处理的 PR。
2. 再用 `gh-pr-review-resolve` 进入单个 PR，整理 unresolved review threads。
3. 如果生成处理记录，默认保存到当前项目：

```text
reviews/<owner>-<repo>-<pr-number>.md
```

例如：

```text
/reviews/keai-skills-1.md
```

处理记录表格统一使用：

```md
| # | Status | ID | Link | Reply | Reply_ZH |
| --- | --- | --- | --- | --- | --- |
```

## 维护约定

- skill 目录名和 `SKILL.md` frontmatter 的 `name` 保持一致。
- skill 名使用小写字母、数字和连字符。
- `description` 只描述触发场景，避免把完整流程塞进 frontmatter。
- 有脚本的 skill，把脚本放在该 skill 自己的 `scripts/` 目录。
- 更新本地安装目录后，同步复制到本仓库的 `skills/` 下。

更多规范见 [docs/creating-skills.md](./docs/creating-skills.md)。
