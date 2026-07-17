# Local Review Record

Use this reference when the user requests `reviewcheck.md`, a local handling record, or a table of review replies.

## Format

```md
PR #<number> unresolved review threads 本地处理记录。

编号按 GitHub unresolved threads 抓取顺序：

| # | Status | ID | Link | Reply | Reply_ZH |
| --- | --- | --- | --- | --- | --- |
| 1 | 已解决 | 3394352828 | [link](https://github.com/...#discussion_r3394352828) | Updated. ... | 已更新。... |
```

- `#`: current live unresolved-thread fetch order.
- `Status`: one of the exact values below.
- `ID`: numeric part of the review anchor; `#discussion_r3394352828` becomes `3394352828`.
- `Link`: GitHub review comment URL.
- `Reply`: copy-ready English GitHub reply.
- `Reply_ZH`: Chinese translation or explanation; keep it local.

## Status Values

| Status | Meaning |
| --- | --- |
| `待处理` | Fetched but not started. |
| `处理中` | A change is in progress. |
| `已解决` | Fixed locally and ready to reply. |
| `已回复` | Replied on GitHub but not confirmed resolved. |
| `已关闭` | Replied and resolved on GitHub. |
| `无需处理` | No code change is required. |
| `需确认` | Product or architectural confirmation is required. |
| `暂缓` | Valid work deferred from this handling batch. |

Default flow: `待处理` -> `处理中` -> `已解决` -> `已回复` -> `已关闭`.

## Saving

Unless the user already chose, ask whether to save and show, show only, save only, or do neither. Default to saving and showing.

Save under `reviews/<owner>-<repo>-<pr-number>.md` relative to the current checkout unless the user supplies a path. Preserve an existing record unless the user approves replacement; use a timestamp suffix for a separate record.

The record branch is complete when its row count matches the fetched thread set, every row uses an allowed status, and a requested file contains the heading, ordering note, and full table.
