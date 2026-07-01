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

## 命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py quota
python3 <skill_dir>/scripts/zlibrary_cli.py profile
```

## 规则

1. 不要在回复中打印密码、token、`remix_userkey`。
2. `profile` 输出会遮蔽 key/token/password 字段。
3. 下载前优先调用 `quota` 或 `getDownloadsLeft()`。
4. 如果登录失败，只提示用户检查凭据或镜像域名，不回显凭据。
