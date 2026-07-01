# API Reference

## 本地基础库

`scripts/Zlibrary.py` 是基础 API 库，保持原样不改。新增能力应在 `scripts/` 新增包装代码。

## 常用方法

| 方法 | 作用 |
| --- | --- |
| `login(email, password)` | 邮箱密码登录 |
| `loginWithToken(remix_userid, remix_userkey)` | token 登录 |
| `search(message, yearFrom, yearTo, languages, extensions, order, page, limit)` | 搜索书籍 |
| `getBookInfo(bookid, hashid)` | 查询书籍详情 |
| `getSimilar(bookid, hashid)` | 查询相似书 |
| `getBookForamt(bookid, hashid)` | 查询可用格式，注意原库方法名拼写是 `Foramt` |
| `downloadBook(book)` | 下载书籍，`book` 至少需要 `id` 和 `hash` |
| `getDownloadsLeft()` | 今日剩余下载次数 |
| `getProfile()` | 用户资料 |
| `getMostPopular()` | 热门书 |
| `getRecently()` | 最近新增 |
| `getUserRecommended()` | 用户推荐 |
| `getUserSaved(order, page, limit)` | 已保存书籍 |
| `getUserDownloaded(order, page, limit)` | 已下载书籍 |

## 已封装命令

```bash
python3 <skill_dir>/scripts/zlibrary_cli.py search "query"
python3 <skill_dir>/scripts/zlibrary_cli.py info --id <id> --hash <hash>
python3 <skill_dir>/scripts/zlibrary_cli.py download --id <id> --hash <hash>
python3 <skill_dir>/scripts/zlibrary_cli.py quota
python3 <skill_dir>/scripts/zlibrary_cli.py profile
```

未封装的方法，先在任务中直接 import `scripts/Zlibrary.py` 验证调用，再考虑是否补进 `scripts/zlibrary_cli.py`。
