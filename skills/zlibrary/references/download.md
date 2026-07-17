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
5. 下载完成后验证文件存在且非空，只报告本地路径、文件大小、剩余额度。

## 注意

- 使用用户已选中的 `id/hash`，不按标题重新搜索替代。
- 文件名必须做非法字符清理。
- 显式 `--filename` 已存在时在下载前停止；服务端文件名冲突时自动选择新路径。只有用户明确要求时才使用 `--force` 覆盖或 `--skip-quota-check` 绕过额度检查。

## 完成条件

确认过的 `id/hash` 已写入目标路径，文件存在且非空，并返回文件大小和可查询到的剩余额度。
