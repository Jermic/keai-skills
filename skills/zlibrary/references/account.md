# account — 账号与额度

## 鉴权

优先 token：

```bash
export ZLIBRARY_REMIX_USERID="..."
export ZLIBRARY_REMIX_USERKEY="..."
```

也支持邮箱密码：

```bash
export ZLIBRARY_EMAIL="..."
export ZLIBRARY_PASSWORD="..."
```

兼容 `zlib-download-skill` 的环境变量：

```bash
export ZLIB_EMAIL="..."
export ZLIB_PASSWORD="..."
```

命令行参数 `--remix-userid/--remix-userkey` 或 `--email/--password` 覆盖环境变量。

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py quota
python3 <skill_dir>/scripts/zlibrary_cli.py profile
```

## 规则

1. 输出只使用遮蔽后的密码、token 和 `remix_userkey`。
2. 下载前调用 `quota` 或 `getDownloadsLeft()`；`null` 或查询错误表示额度未知，不等于 `0`。
3. 登录失败时提示检查凭据或镜像域名，只返回非敏感错误信息。

## 完成条件

- `quota`：返回明确的剩余额度；查询失败则明确报告未知。
- `profile`：返回资料且所有 key、token、password 字段均已遮蔽。
