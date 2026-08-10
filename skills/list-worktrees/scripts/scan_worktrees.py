#!/usr/bin/env python3
"""Print a read-only Markdown inventory of Git worktrees."""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


TABLE_HEADER = "| 序号 | 项目名 | Worktree | 分支 / HEAD | 工作区 | 远端情况 |"
TABLE_RULE = "| ---: | --- | --- | --- | --- | --- |"


class ScanError(RuntimeError):
    pass


def run(args: list[str], cwd: Path, *, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ScanError(f"{' '.join(args)}: {message}")
    return result.stdout.strip()


def succeeds(args: list[str], cwd: Path) -> bool:
    return subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


@dataclass(frozen=True)
class Worktree:
    project: str
    repo: Path
    path: Path
    head: str
    branch: str | None


@dataclass(frozen=True)
class RemoteHeads:
    heads: dict[str, str] | None


def parse_worktrees(raw: str, repo: Path, project: str) -> list[Worktree]:
    worktrees: list[Worktree] = []
    for record in filter(str.strip, raw.split("\n\n")):
        fields: dict[str, str] = {}
        for line in record.splitlines():
            key, _, value = line.partition(" ")
            if value:
                fields[key] = value
        branch_ref = fields.get("branch")
        worktrees.append(
            Worktree(
                project=project,
                repo=repo,
                path=Path(fields["worktree"]),
                head=fields["HEAD"],
                branch=branch_ref.removeprefix("refs/heads/") if branch_ref else None,
            )
        )
    return worktrees


def repo_root(path: Path) -> Path:
    if not path.exists():
        raise ScanError(f"路径无效：{path}")
    root = run(["git", "rev-parse", "--show-toplevel"], path, check=False)
    if not root:
        raise ScanError(f"不是 Git 工作区：{path}")
    return Path(root).resolve()


def project_name(repo: Path) -> str:
    remote = run(["git", "remote", "get-url", "origin"], repo, check=False)
    if remote:
        name = remote.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        return name.removesuffix(".git") or repo.name
    common = Path(run(["git", "rev-parse", "--git-common-dir"], repo))
    if common.name == ".git":
        return common.parent.name
    return repo.name


def registered_worktrees(path: Path) -> list[Worktree]:
    root = repo_root(path)
    return parse_worktrees(
        run(["git", "worktree", "list", "--porcelain"], root),
        root,
        project_name(root),
    )


def discover_agent_worktrees(root: Path) -> list[Path]:
    if not root.is_dir():
        raise ScanError(f"路径无效：{root}")
    found: list[Path] = []
    for current, directories, files in os.walk(root):
        directories.sort()
        if ".git" in directories or ".git" in files:
            found.append(Path(current).resolve())
            directories.clear()
    return found


def scan_projects(paths: list[Path]) -> list[Worktree]:
    worktrees: dict[Path, Worktree] = {}
    for path in paths:
        for item in registered_worktrees(path.expanduser().resolve()):
            worktrees[item.path.resolve()] = item
    return list(worktrees.values())


def scan_agent_roots(paths: list[Path]) -> list[Worktree]:
    worktrees: dict[Path, Worktree] = {}
    for root in paths:
        for path in discover_agent_worktrees(root.expanduser().resolve()):
            repo = repo_root(path)
            item = next(
                (candidate for candidate in registered_worktrees(repo) if candidate.path.resolve() == path),
                None,
            )
            if item:
                worktrees[path] = item
    return list(worktrees.values())


def workspace_status(path: Path) -> str:
    if not path.is_dir():
        return "路径不存在"
    result = subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain=v2", "-z", "--untracked-files=all"],
        cwd=path,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return "状态读取失败"
    raw = result.stdout
    staged = unstaged = untracked = 0
    records = raw.split(b"\0")
    skip = False
    for record in records:
        if skip:
            skip = False
            continue
        if not record:
            continue
        kind = record[:1]
        if kind == b"?":
            untracked += 1
            continue
        if kind not in {b"1", b"2", b"u"}:
            continue
        fields = record.split(b" ", 2)
        xy = fields[1].decode("ascii", errors="replace")
        staged += xy[0] != "."
        unstaged += xy[1] != "."
        skip = kind == b"2"
    if not (staged or unstaged or untracked):
        return "干净"
    return f"暂存 {staged}；未暂存 {unstaged}；未跟踪 {untracked}"


def branch_upstream(repo: Path, branch: str) -> tuple[str, str, str] | None:
    raw = run(
        [
            "git",
            "for-each-ref",
            "--format=%(upstream:remotename)%00%(upstream:remoteref)%00%(upstream)",
            f"refs/heads/{branch}",
        ],
        repo,
    )
    if not raw:
        return None
    remote, remote_ref, tracking_ref = raw.split("\x00")
    if not remote or remote == "." or not remote_ref:
        return None
    return remote, remote_ref, tracking_ref


def relation(repo: Path, local: str, other: str) -> str | None:
    if not succeeds(["git", "cat-file", "-e", f"{other}^{{commit}}"], repo):
        return None
    raw = run(["git", "rev-list", "--left-right", "--count", f"{local}...{other}"], repo)
    ahead, behind = map(int, raw.split())
    if not ahead and not behind:
        return "与远端同步"
    if ahead and behind:
        return f"diverged（ahead {ahead}，behind {behind}）"
    if ahead:
        return f"ahead {ahead}"
    return f"behind {behind}"


def read_remote_heads(repo: Path, remote: str) -> RemoteHeads:
    url = run(["git", "remote", "get-url", remote], repo, check=False)
    if not url:
        return RemoteHeads(None)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=3",
        }
    )
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            cwd=repo,
            text=True,
            capture_output=True,
            timeout=6,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return RemoteHeads(None)
    if result.returncode:
        return RemoteHeads(None)
    heads = {}
    for line in result.stdout.splitlines():
        sha, ref = line.split("\t", 1)
        heads[ref] = sha
    return RemoteHeads(heads)


def format_remote_status(
    prefix: str,
    heads: dict[str, str] | None,
    remote_ref: str,
    live: str | None,
    cached: str | None = None,
) -> str:
    if heads is None:
        suffix = f"（本地 tracking：{cached}，非实时）" if cached else ""
        return f"{prefix}无法联网验证{suffix}"
    remote_sha = heads.get(remote_ref)
    if not remote_sha:
        return f"{prefix}远端分支不存在"
    if live:
        return f"{prefix}{live}"
    return f"{prefix}远端已验证为 {remote_sha[:8]}；ahead/behind 无法比较"


def remote_relation(
    item: Worktree,
    branch: str,
    cache: dict[tuple[Path, str], RemoteHeads],
) -> str:
    upstream = branch_upstream(item.repo, branch)
    if upstream:
        remote, remote_ref, tracking_ref = upstream
        prefix = ""
    else:
        remote, remote_ref, tracking_ref = "origin", f"refs/heads/{branch}", ""
        prefix = "无 upstream；"
        if not run(["git", "remote", "get-url", remote], item.repo, check=False):
            return f"{prefix}无 origin"
    common = Path(run(["git", "rev-parse", "--git-common-dir"], item.repo))
    if not common.is_absolute():
        common = (item.repo / common).resolve()
    key = (common, remote)
    if key not in cache:
        cache[key] = read_remote_heads(item.repo, remote)
    result = cache[key]
    remote_sha = result.heads.get(remote_ref) if result.heads else None
    live = relation(item.repo, branch, remote_sha) if remote_sha else None
    cached = relation(item.repo, branch, tracking_ref) if result.heads is None and tracking_ref else None
    return format_remote_status(prefix, result.heads, remote_ref, live, cached)


def detached_relation(item: Worktree, cache: dict[tuple[Path, str], RemoteHeads]) -> str:
    branches = run(
        ["git", "for-each-ref", "--points-at", item.head, "--format=%(refname:short)", "refs/heads"],
        item.repo,
    ).splitlines()
    if not branches:
        return f"detached 基准：{item.head[:8]}（无 upstream）"
    ordered = sorted(branches)
    branch = next((name for name in ordered if branch_upstream(item.repo, name)), ordered[0])
    return f"detached 基准：{branch}；{remote_relation(item, branch, cache)}"


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(worktrees: list[Worktree], error: str | None = None) -> str:
    lines = [TABLE_HEADER, TABLE_RULE]
    if error:
        lines.append(f"| — | — | {cell(error)} | — | — | — |")
        return "\n".join(lines)
    if not worktrees:
        lines.append("| — | — | 未发现 worktree | — | — | — |")
        return "\n".join(lines)
    cache: dict[tuple[Path, str], RemoteHeads] = {}
    ordered = sorted(worktrees, key=lambda item: (item.project.casefold(), str(item.path).casefold(), str(item.path)))
    for index, item in enumerate(ordered, 1):
        branch_head = f"{item.branch} @ {item.head[:8]}" if item.branch else f"detached @ {item.head[:8]}"
        remote = remote_relation(item, item.branch, cache) if item.branch else detached_relation(item, cache)
        lines.append(
            f"| {index} | {cell(item.project)} | {cell(item.path)} | {cell(branch_head)} | "
            f"{cell(workspace_status(item.path))} | {cell(remote)} |"
        )
    return "\n".join(lines)


def self_check() -> None:
    sample = "worktree /tmp/b\nHEAD bbbbbbbb\ndetached\n\nworktree /tmp/a\nHEAD aaaaaaaa\nbranch refs/heads/main\n"
    parsed = parse_worktrees(sample, Path("/tmp/a"), "demo")
    assert [item.branch for item in parsed] == [None, "main"]
    head = {"refs/heads/topic": "a" * 40}
    assert format_remote_status("无 upstream；", head, "refs/heads/topic", "与远端同步") == "无 upstream；与远端同步"
    assert format_remote_status("无 upstream；", head, "refs/heads/missing", None) == "无 upstream；远端分支不存在"
    assert format_remote_status("无 upstream；", None, "refs/heads/topic", None) == "无 upstream；无法联网验证"
    assert render([]).splitlines() == [TABLE_HEADER, TABLE_RULE, "| — | — | 未发现 worktree | — | — | — |"]
    assert cell("a|b\nc") == "a\\|b c"
    print("self-check passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="List Git worktrees without changing repository state.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project", nargs="+", metavar="PATH")
    scope.add_argument("--agent-root", nargs="+", metavar="PATH")
    parser.add_argument("--self-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.self_check:
        self_check()
        return 0
    if not args.project and not args.agent_root:
        print(render([], "未指定扫描范围"))
        return 0
    try:
        paths = [Path(value) for value in args.project or args.agent_root]
        worktrees = scan_projects(paths) if args.project else scan_agent_roots(paths)
        print(render(worktrees))
    except (OSError, ScanError, ValueError) as error:
        print(render([], str(error)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
