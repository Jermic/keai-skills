# download — 下载书籍

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py download --id <book-id> --hash <book-hash> -o ~/Downloads
```

## 工作流

1. 已有明确 `id/hash` 或用户已选中本轮结果时直接沿用；只有目标不明确时才搜索并让用户选择。
2. 调用 `scripts/zlibrary_cli.py download`。CLI 已在下载前检查额度，并在结束后返回剩余额度，不额外运行 `quota`。
3. 直接使用底层 API 时才自行检查 `getDownloadsLeft()`，额度为 0 时停止；未知额度明确报告，不当作 0。
4. 保留 CLI 的文件名清理、冲突处理和空文件检查；需要底层 API 扩展时沿用这些保护。
5. 下载完成后验证文件存在且非空，只报告本地路径、文件大小、剩余额度。

## 注意

- 使用用户已选中的 `id/hash`，不按标题重新搜索替代。
- 文件名必须做非法字符清理。
- 显式 `--filename` 已存在时在下载前停止；服务端文件名冲突时自动选择新路径。只有用户明确要求时才使用 `--force` 覆盖或 `--skip-quota-check` 绕过额度检查。

## 完成条件

确认过的 `id/hash` 已写入目标路径，文件存在且非空，并返回文件大小和可查询到的剩余额度。
