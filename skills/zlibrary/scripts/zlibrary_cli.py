#!/usr/bin/env python3
"""Small CLI over the bundled scripts/Zlibrary.py wrapper."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from Zlibrary import Zlibrary  # noqa: E402

DEFAULT_DOMAIN = "z-library.sk"


def make_api(args: argparse.Namespace) -> Zlibrary:
    api = Zlibrary()
    domain = (args.domain or DEFAULT_DOMAIN).strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    if domain:
        setattr(api, "_Zlibrary__domain", domain)

    remix_userid = args.remix_userid or os.environ.get("ZLIBRARY_REMIX_USERID")
    remix_userkey = args.remix_userkey or os.environ.get("ZLIBRARY_REMIX_USERKEY")
    email = args.email or os.environ.get("ZLIBRARY_EMAIL") or os.environ.get("ZLIB_EMAIL")
    password = args.password or os.environ.get("ZLIBRARY_PASSWORD") or os.environ.get("ZLIB_PASSWORD")

    if remix_userid and remix_userkey:
        ensure_success(api.loginWithToken(remix_userid, remix_userkey), "token login")
    elif email and password:
        ensure_success(api.login(email, password), "email login")
    else:
        raise RuntimeError("set ZLIBRARY_REMIX_USERID/ZLIBRARY_REMIX_USERKEY or ZLIBRARY_EMAIL/ZLIBRARY_PASSWORD")
    return api


def ensure_success(response: dict | None, stage: str) -> None:
    if not response or response.get("success") is False:
        raise RuntimeError(f"{stage} failed: {(response or {}).get('message') or response}")


def cmd_search(args: argparse.Namespace) -> None:
    response = make_api(args).search(
        message=args.query,
        yearFrom=args.year_from,
        yearTo=args.year_to,
        languages=args.language,
        extensions=args.extension,
        order=args.order,
        page=args.page,
        limit=args.limit,
    ) or {}
    ensure_success(response, "search")
    books = [normalize_book(book) for book in response.get("books") or response.get("results") or []]
    if args.json:
        payload = {"query": args.query, "count": len(books), "books": books}
        if args.raw:
            payload["response"] = response
        else:
            for book in books:
                book.pop("raw", None)
        print_json(payload)
        return
    print_books(books)


def cmd_info(args: argparse.Namespace) -> None:
    response = make_api(args).getBookInfo(args.id, args.hash)
    ensure_success(response, "info")
    print_json(response)


def cmd_download(args: argparse.Namespace) -> None:
    api = make_api(args)
    if not args.skip_quota_check:
        left = safe_downloads_left(api)
        if left is not None and left <= 0:
            raise RuntimeError("download quota is exhausted")
    filename, content = api.downloadBook({"id": args.id, "hash": args.hash})
    output_dir = Path(args.output).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / safe_filename(args.filename or filename)
    target.write_bytes(content)
    print_json({"status": "ok", "path": str(target), "size": len(content), "downloads_left": safe_downloads_left(api)})


def cmd_quota(args: argparse.Namespace) -> None:
    print_json({"downloads_left": safe_downloads_left(make_api(args))})


def cmd_profile(args: argparse.Namespace) -> None:
    response = make_api(args).getProfile()
    ensure_success(response, "profile")
    print_json(mask_secrets(response))


def safe_downloads_left(api: Zlibrary) -> int | None:
    try:
        value = api.getDownloadsLeft()
        return int(value) if value is not None else None
    except Exception:
        return None


def normalize_book(book: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": value(book, "title"),
        "author": value(book, "author"),
        "year": value(book, "year"),
        "language": value(book, "language"),
        "extension": clean_extension(value(book, "extension")),
        "size": value(book, "filesizeString") or value(book, "size"),
        "publisher": value(book, "publisher"),
        "isbn": isbn(book),
        "id": value(book, "id"),
        "hash": value(book, "hash"),
        "url": value(book, "url") or value(book, "href"),
        "raw": book,
    }


def value(book: dict[str, Any], key: str) -> str | None:
    found = book.get(key)
    if found is None:
        return None
    text = str(found).strip()
    return text or None


def clean_extension(found: str | None) -> str | None:
    return found.lower().lstrip(".") if found else None


def isbn(book: dict[str, Any]) -> str | None:
    for key in ("isbn", "isbn10", "isbn13"):
        found = value(book, key)
        if found:
            return found.replace("-", "").replace(" ", "").upper()
    identifiers = book.get("identifiers")
    if isinstance(identifiers, dict):
        for key in ("isbn_13", "isbn_10", "isbn13", "isbn10", "isbn"):
            found = identifiers.get(key)
            if found:
                return str(found).replace("-", "").replace(" ", "").upper()
    return None


def print_books(books: list[dict[str, Any]]) -> None:
    if not books:
        print("No Z-Library results found.")
        return
    print("| # | Title | Author | Year | Lang | Ext | Size | ID / Hash | ISBN | URL |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for index, book in enumerate(books, 1):
        print("| " + " | ".join([
            str(index),
            cell(book.get("title")),
            cell(book.get("author")),
            cell(book.get("year")),
            cell(book.get("language")),
            cell(book.get("extension")),
            cell(book.get("size")),
            cell(" / ".join(part for part in [book.get("id"), book.get("hash")] if part)),
            cell(book.get("isbn")),
            cell(book.get("url")),
        ]) + " |")


def cell(text: object) -> str:
    return str(text or "-").replace("|", "\\|").replace("\n", " ")


def safe_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def mask_secrets(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: ("***" if any(word in key.lower() for word in ("key", "token", "password")) else mask_secrets(value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [mask_secrets(item) for item in data]
    return data


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def add_auth_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--domain", default=os.environ.get("ZLIBRARY_DOMAIN", DEFAULT_DOMAIN))
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--remix-userid")
    parser.add_argument("--remix-userkey")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zlibrary_cli.py", description="Z-Library API helper using bundled scripts/Zlibrary.py")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search books")
    add_auth_flags(search)
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--language")
    search.add_argument("--extension", action="append")
    search.add_argument("--order")
    search.add_argument("--year-from", type=int)
    search.add_argument("--year-to", type=int)
    search.add_argument("--json", action="store_true")
    search.add_argument("--raw", action="store_true")
    search.set_defaults(func=cmd_search)

    info = sub.add_parser("info", help="Get book details by id/hash")
    add_auth_flags(info)
    info.add_argument("--id", required=True)
    info.add_argument("--hash", required=True)
    info.set_defaults(func=cmd_info)

    download = sub.add_parser("download", help="Download a book by id/hash")
    add_auth_flags(download)
    download.add_argument("--id", required=True)
    download.add_argument("--hash", required=True)
    download.add_argument("-o", "--output", default=str(Path.home() / "Downloads"))
    download.add_argument("--filename")
    download.add_argument("--skip-quota-check", action="store_true")
    download.set_defaults(func=cmd_download)

    quota = sub.add_parser("quota", help="Show remaining download quota")
    add_auth_flags(quota)
    quota.set_defaults(func=cmd_quota)

    profile = sub.add_parser("profile", help="Show masked account profile")
    add_auth_flags(profile)
    profile.set_defaults(func=cmd_profile)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"zlibrary failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
