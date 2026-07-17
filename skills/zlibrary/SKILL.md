---
name: zlibrary
description: "Use when the user wants a Z-Library book workflow: search, inspect metadata or formats, download a chosen book, check an account profile or quota, or use the bundled API wrapper."
---

# Zlibrary

通过内置 `scripts/Zlibrary.py` 调用 Z-Library EAPI。优先用脚本完成稳定动作；更细的 API 能力先读对应 reference。

## 能力

| 能力 | 用户例子 | 入口 | 详细说明 |
| --- | --- | --- | --- |
| 搜索书籍 | "搜一下三体" "找英文版 deep learning" | `scripts/zlibrary_cli.py search` | `references/search.md` |
| 书籍信息 | "看这个 id/hash 的详情" | `scripts/zlibrary_cli.py info` | `references/book.md` |
| 下载书籍 | "下载第 2 本" | `scripts/zlibrary_cli.py download` | `references/download.md` |
| 账号与额度 | "还剩几次下载" "检查账号" | `scripts/zlibrary_cli.py quota/profile` | `references/account.md` |
| API 扩展 | "用 Zlibrary.py 的某个接口" | import `scripts/Zlibrary.py` | `references/api_reference.md` |

## 通用规则

1. 根据用户意图先读对应 `references/*.md`；该分支的完成条件也在对应 reference 中。
2. 保持 `scripts/Zlibrary.py` 原样；新增能力在 `scripts/` 包装并 import 基础库。
3. 输出只包含遮蔽后的鉴权信息。
4. 下载前先让用户从搜索结果里确认目标，除非用户已经给出明确的 `id` 和 `hash`。
5. 搜索结果默认用编号表格展示，方便用户后续说"下载第 2 本"。

## 鉴权

调用 Z-Library 网络接口时需要鉴权，先读 `references/account.md`。只查看本地 API、运行 self-check 或修改包装代码时不索取凭据。
