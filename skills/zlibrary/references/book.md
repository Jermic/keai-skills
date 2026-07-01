# book — 书籍信息

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py info --id <book-id> --hash <book-hash>
```

## API

使用 `scripts/Zlibrary.py`：

```python
api.getBookInfo(bookid, hashid)
api.getSimilar(bookid, hashid)
api.getBookForamt(bookid, hashid)
```

## 工作流

1. 如果用户只给书名，先用 `search` 找候选并让用户确认。
2. 如果用户给出 `id/hash`，直接查 `info`。
3. 展示详情时优先说明标题、作者、出版社、年份、语言、格式、ISBN、简介、可用格式。
4. 如果要继续下载，沿用同一个 `id/hash`。
