# download — 下载书籍

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py download --id <book-id> --hash <book-hash> -o ~/Downloads
```

## 工作流

1. 先搜索并展示编号结果。
2. 等用户选择编号，取该结果的 `id` 和 `hash`。
3. 下载前默认检查 `getDownloadsLeft()`；额度为 0 时不要下载。
4. 调用 `scripts/Zlibrary.py` 的 `downloadBook({"id": id, "hash": hash})`。
5. 下载完成后只报告本地路径、文件大小、剩余额度。

## 注意

- 不要修改 `scripts/Zlibrary.py`，下载逻辑缺口在 `scripts/zlibrary_cli.py` 外层补。
- 不要用标题重新搜索来替代用户已选中的 `id/hash`。
- 文件名必须做非法字符清理。
