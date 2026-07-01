# search — 搜索书籍

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py search "三体" --limit 10
python3 <skill_dir>/scripts/zlibrary_cli.py search "deep learning" --language english --extension pdf --json
```

## 参数

| 参数 | 说明 |
| --- | --- |
| `query` | 搜索词，必填 |
| `--limit` | 返回数量，默认 10 |
| `--page` | 页码，默认 1 |
| `--language` | 传给 `Zlibrary.search(languages=...)` |
| `--extension` | 可重复，传给 `Zlibrary.search(extensions=...)` |
| `--order` | 传给 Z-Library 排序参数 |
| `--year-from` / `--year-to` | 出版年份范围 |
| `--json` | 输出结构化 JSON |
| `--raw` | 搭配 `--json` 保留原始 API 回包 |

## 工作流

1. 搜索时调用 `scripts/Zlibrary.py` 的 `search(message=..., limit=...)`。
2. 展示编号表格，至少包含书名、作者、年份、语言、格式、大小、`id/hash`。
3. 如果用户后续要下载，必须用同一轮结果里的 `id` 和 `hash`，不要只按标题重新猜。
4. 需要排查字段缺失时用 `--json --raw`。
