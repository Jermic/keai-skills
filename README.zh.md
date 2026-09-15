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
gh-pr-review
gh-local-cleanup
gh-release-prepare
list-worktrees
migrate-codex-worktree
notion-sync-markdown
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
    ├── gh-pr-review/
    ├── gh-local-cleanup/
    ├── gh-release-prepare/
    ├── list-worktrees/
    ├── migrate-codex-worktree/
    ├── notion-sync-markdown/
    └── zlibrary/
```

- `skills/`: 每个子目录是一个独立 skill，必须包含 `SKILL.md`。
- `docs/`: 维护规范、创建新 skill 的约定，以及未来可能加入的发布说明。
- `scripts/`: 只在需要仓库级脚本时添加；目前每个 skill 自带自己的 `scripts/`。

## 可用 Skills

| Skill | 作用 | 什么时候用 | 单独安装 |
| --- | --- | --- | --- |
| `gh-pr-review` | PR review 总览、评论分析、回复草稿与授权处理 | 按意图或指定 scan / inspect / draft / record / reply / resolve 进入对应流程 | `npx skills add <github-owner>/keai-skills/skills/gh-pr-review` |
| `gh-local-cleanup` | 对照 GitHub 状态审计本地 branch 和 worktree | 想在删除本地 review checkout、已合并分支或完成的 worktree 前先获得分类清单 | `npx skills add <github-owner>/keai-skills/skills/gh-local-cleanup` |
| `gh-release-prepare` | 准备独立的功能与版本升级发布 PR | 准备独立的功能与版本升级发布 PR | `npx skills add <github-owner>/keai-skills/skills/gh-release-prepare` |
| `list-worktrees` | 查看 worktree 的本地和远端状态 | 查看 worktree 的本地和远端状态 | `npx skills add <github-owner>/keai-skills/skills/list-worktrees` |
| `migrate-codex-worktree` | 在 Codex worktree 移动后生成任务修复命令 | 在 Codex worktree 移动后生成任务修复命令 | `npx skills add <github-owner>/keai-skills/skills/migrate-codex-worktree` |
| `notion-sync-markdown` | 用最小 block 替换将本地 Markdown 同步到现有 Notion 页面 | 本地 Markdown 是真源，并需要尽量保留未变 block 与 discussions | `npx skills add <github-owner>/keai-skills/skills/notion-sync-markdown` |
| `zlibrary` | 用内置 `Zlibrary.py` 处理 Z-Library 书籍 | 想搜索候选书、查看详情、下载选中的书、检查账号额度，或扩展 Z-Library API 能力 | `npx skills add <github-owner>/keai-skills/skills/zlibrary` |

## GitHub PR Review 工作流

`gh-pr-review` 根据意图或明确指定的 `scan / inspect / draft / record / reply / resolve` 选择子流程。它们可独立进入，不要求先 scan；PR 链接读取全部 unresolved threads，comment 链接只读取目标及必要父评论。拟稿采用简短、直接、以最终代码为准的 [回复风格](skills/gh-pr-review/references/reply-style.md)。

默认在聊天中输出，保存和远端操作按请求执行。[处理记录](skills/gh-pr-review/references/review-record.md) 和 [判断／状态](skills/gh-pr-review/references/reporting.md) 各自保持单一来源。

### 从旧名称迁移

`gh-pr-review-scan` 和 `gh-pr-review-resolve` 已合并为 `gh-pr-review`，仓库不再提供旧入口。安装新 Skill 后，确认本地定制已保留，再通过原安装方式移除旧的两个安装副本，避免重复触发。旧的 scan 请求使用 `gh-pr-review scan`；原评论分析使用 `inspect`，拟回复使用 `draft`，关闭线程才使用 `resolve`。这些是对 agent 的模式指令，不是脚本子命令。

## 维护约定

- skill 目录名和 `SKILL.md` frontmatter 的 `name` 保持一致。
- skill 名使用小写字母、数字和连字符。
- `description` 只描述触发场景，避免把完整流程塞进 frontmatter。
- 有脚本的 skill，把脚本放在该 skill 自己的 `scripts/` 目录。
- 更新本地安装目录后，同步复制到本仓库的 `skills/` 下。

更多规范见 [docs/creating-skills.md](./docs/creating-skills.md)。
