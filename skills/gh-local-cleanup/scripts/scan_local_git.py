#!/usr/bin/env python3
"""Classify local Git branches and worktrees using remote and GitHub PR state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATEGORY_ORDER = {"BLOCKED": 0, "KEEP": 1, "CONFIRM": 2, "DELETE": 3}


class CommandError(RuntimeError):
    pass


def run(args: list[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise CommandError(f"{' '.join(args)}: {message}")
    return result.stdout.strip()


def succeeds(args: list[str], cwd: Path) -> bool:
    return subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def parse_json_documents(raw: str) -> list[Any]:
    decoder = json.JSONDecoder()
    documents: list[Any] = []
    index = 0
    while index < len(raw):
        while index < len(raw) and raw[index].isspace():
            index += 1
        if index < len(raw):
            document, index = decoder.raw_decode(raw, index)
            documents.append(document)
    return documents


def github_repo(cwd: Path) -> tuple[str, str]:
    remote = run(["git", "remote", "get-url", "origin"], cwd)
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", remote)
    if not match:
        raise CommandError(f"Cannot parse GitHub origin: {remote}")
    return match.group("owner"), match.group("repo")


def default_ref(cwd: Path) -> str:
    symbolic = run(
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        cwd,
        check=False,
    )
    if symbolic:
        return symbolic
    for candidate in ("origin/main", "origin/master"):
        if succeeds(["git", "rev-parse", "--verify", candidate], cwd):
            return candidate
    raise CommandError("Cannot find origin's default branch")


def ahead_behind(cwd: Path, left: str, right: str) -> tuple[int, int]:
    raw = run(["git", "rev-list", "--left-right", "--count", f"{left}...{right}"], cwd)
    left_only, right_only = raw.split()
    return int(left_only), int(right_only)


@dataclass(frozen=True)
class PullRequest:
    number: int
    state: str
    merged: bool
    author: str
    title: str
    url: str
    updated_at: str


def fetch_pull_requests(cwd: Path, owner: str, repo: str) -> dict[str, list[PullRequest]]:
    raw = run(
        [
            "gh",
            "api",
            "--paginate",
            f"/repos/{owner}/{repo}/pulls?state=all&per_page=100",
        ],
        cwd,
    )
    by_branch: dict[str, list[PullRequest]] = {}
    for document in parse_json_documents(raw):
        for item in document:
            branch = item.get("head", {}).get("ref")
            if not branch:
                continue
            by_branch.setdefault(branch, []).append(
                PullRequest(
                    number=int(item["number"]),
                    state=str(item["state"]),
                    merged=bool(item.get("merged_at")),
                    author=str(item.get("user", {}).get("login") or "unknown"),
                    title=str(item["title"]),
                    url=str(item["html_url"]),
                    updated_at=str(item.get("updated_at") or ""),
                )
            )
    return by_branch


def representative_pr(pull_requests: list[PullRequest]) -> PullRequest | None:
    if not pull_requests:
        return None
    rank = lambda pr: (2 if pr.state == "open" else 1 if pr.merged else 0, pr.updated_at)
    return max(pull_requests, key=rank)


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str
    branch: str | None
    detached: bool
    locked: bool
    prunable: bool
    dirty: bool


def read_worktrees(cwd: Path) -> list[Worktree]:
    raw = run(["git", "worktree", "list", "--porcelain"], cwd)
    records = [record for record in raw.split("\n\n") if record.strip()]
    worktrees: list[Worktree] = []
    for record in records:
        fields: dict[str, str] = {}
        flags: set[str] = set()
        for line in record.splitlines():
            key, _, value = line.partition(" ")
            if value:
                fields[key] = value
            else:
                flags.add(key)
        path = Path(fields["worktree"])
        branch_ref = fields.get("branch")
        branch = branch_ref.removeprefix("refs/heads/") if branch_ref else None
        dirty = path.exists() and bool(run(["git", "status", "--porcelain"], path))
        worktrees.append(
            Worktree(
                path=path,
                head=fields["HEAD"],
                branch=branch,
                detached="detached" in flags,
                locked="locked" in fields or "locked" in flags,
                prunable="prunable" in fields or "prunable" in flags,
                dirty=dirty,
            )
        )
    return worktrees


@dataclass(frozen=True)
class BranchEvidence:
    name: str
    is_default: bool
    is_backup: bool
    checked_out: bool
    dirty_worktree: bool
    upstream_exists: bool
    remote_equal: bool
    ahead: int
    in_default: bool
    merged_pr: bool
    pr: PullRequest | None
    current_user: str


def classify_branch(evidence: BranchEvidence) -> tuple[str, str]:
    if evidence.is_default:
        return "KEEP", "default branch"
    if evidence.dirty_worktree:
        return "BLOCKED", "checked out in a dirty worktree"
    if evidence.is_backup:
        return "KEEP", "backup branch"
    if evidence.ahead > 0 and not evidence.in_default:
        return "KEEP", f"{evidence.ahead} local-only commit(s)"
    if evidence.pr and evidence.pr.state == "open" and evidence.pr.author == evidence.current_user:
        return "KEEP", f"own open PR #{evidence.pr.number}"

    if evidence.merged_pr and evidence.pr:
        category, reason = "DELETE", f"merged PR #{evidence.pr.number}"
    elif evidence.in_default:
        category, reason = "DELETE", "contained in the default branch"
    elif evidence.pr and evidence.pr.state == "open" and evidence.pr.author != evidence.current_user:
        if evidence.upstream_exists and evidence.ahead == 0:
            category, reason = "DELETE", f"review checkout for @{evidence.pr.author} PR #{evidence.pr.number}"
        else:
            category, reason = "KEEP", "review branch has unpreserved local state"
    elif evidence.upstream_exists and evidence.remote_equal:
        reason = (
            f"closed unmerged PR #{evidence.pr.number}; remote preserves the tip"
            if evidence.pr
            else "remote preserves the tip; intent is unknown"
        )
        category = "CONFIRM"
    elif not evidence.upstream_exists:
        category, reason = "KEEP", "unmerged local-only branch"
    else:
        category, reason = "KEEP", "remote and local state differ"

    if evidence.checked_out and category == "DELETE":
        return "CONFIRM", f"{reason}; switch or remove its worktree first"
    return category, reason


@dataclass(frozen=True)
class BranchReport:
    category: str
    name: str
    upstream: str
    relation: str
    default_relation: str
    pr: PullRequest | None
    reason: str


def read_branches(
    cwd: Path,
    default: str,
    current_user: str,
    pull_requests: dict[str, list[PullRequest]],
    worktrees: list[Worktree],
) -> list[BranchReport]:
    fmt = "%00".join(
        (
            "%(refname:short)",
            "%(objectname)",
            "%(upstream:short)",
            "%(committerdate:short)",
        )
    )
    raw = run(["git", "for-each-ref", "refs/heads", f"--format={fmt}"], cwd)
    checked = {worktree.branch: worktree for worktree in worktrees if worktree.branch}
    default_name = default.removeprefix("origin/")
    reports: list[BranchReport] = []

    for line in raw.splitlines():
        name, sha, upstream, _date = line.split("\x00")
        upstream_exists = bool(upstream) and succeeds(
            ["git", "rev-parse", "--verify", upstream], cwd
        )
        remote_equal = upstream_exists and run(["git", "rev-parse", upstream], cwd) == sha
        behind = ahead = 0
        if upstream_exists:
            behind, ahead = ahead_behind(cwd, upstream, name)
            relation = "equal" if not behind and not ahead else f"ahead {ahead}, behind {behind}"
        elif upstream:
            relation = "gone"
        else:
            relation = "none"

        default_behind, default_ahead = ahead_behind(cwd, default, name)
        in_default = succeeds(["git", "merge-base", "--is-ancestor", sha, default], cwd)
        default_relation = (
            "contained"
            if in_default
            else f"ahead {default_ahead}, behind {default_behind}"
        )
        prs = pull_requests.get(name, [])
        pr = representative_pr(prs)
        worktree = checked.get(name)
        evidence = BranchEvidence(
            name=name,
            is_default=name == default_name,
            is_backup=name.startswith(("backup/", "backup-", "chore/backup-")),
            checked_out=worktree is not None,
            dirty_worktree=bool(worktree and worktree.dirty),
            upstream_exists=upstream_exists,
            remote_equal=remote_equal,
            ahead=ahead if upstream_exists else default_ahead,
            in_default=in_default,
            merged_pr=bool(pr and pr.merged),
            pr=pr,
            current_user=current_user,
        )
        category, reason = classify_branch(evidence)
        reports.append(
            BranchReport(
                category=category,
                name=name,
                upstream=upstream or "-",
                relation=relation,
                default_relation=default_relation,
                pr=pr,
                reason=reason,
            )
        )
    return sorted(reports, key=lambda item: (CATEGORY_ORDER[item.category], item.name))


@dataclass(frozen=True)
class WorktreeReport:
    category: str
    path: Path
    branch: str
    dirty: bool
    reason: str


def worktree_decision(
    *,
    primary: bool,
    locked: bool,
    prunable: bool,
    exists: bool,
    dirty: bool,
    detached: bool,
    detached_in_default: bool,
) -> tuple[str, str]:
    if dirty:
        return "BLOCKED", "uncommitted changes"
    if primary:
        return "KEEP", "primary checkout"
    if locked:
        return "KEEP", "locked worktree"
    if prunable or not exists:
        return "CONFIRM", "missing/prunable worktree registration"
    if detached:
        if detached_in_default:
            return "DELETE", "clean detached checkout contained in default branch"
        return "CONFIRM", "detached commit is not contained in default branch"
    return "DELETE", "clean secondary worktree; remove worktree only"


def classify_worktrees(cwd: Path, default: str, worktrees: list[Worktree]) -> list[WorktreeReport]:
    reports: list[WorktreeReport] = []
    for index, worktree in enumerate(worktrees):
        branch = worktree.branch or f"detached@{worktree.head[:8]}"
        detached_in_default = worktree.detached and succeeds(
            ["git", "merge-base", "--is-ancestor", worktree.head, default], cwd
        )
        category, reason = worktree_decision(
            primary=index == 0,
            locked=worktree.locked,
            prunable=worktree.prunable,
            exists=worktree.path.exists(),
            dirty=worktree.dirty,
            detached=worktree.detached,
            detached_in_default=detached_in_default,
        )
        reports.append(WorktreeReport(category, worktree.path, branch, worktree.dirty, reason))
    return sorted(reports, key=lambda item: (CATEGORY_ORDER[item.category], str(item.path)))


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def print_report(
    root: Path,
    github: str,
    default: str,
    current_user: str,
    branches: list[BranchReport],
    worktrees: list[WorktreeReport],
) -> None:
    print(f"## {root.name}")
    print()
    print(f"- Path: `{root}`")
    print(f"- GitHub: `{github}`")
    print(f"- Default: `{default}`")
    print(f"- Authenticated user: `@{current_user}`")
    print()
    print("### Worktrees")
    print()
    print("| Category | Path | Branch/HEAD | Dirty | Reason |")
    print("|---|---|---|---:|---|")
    for item in worktrees:
        print(
            f"| {item.category} | `{cell(item.path)}` | `{cell(item.branch)}` "
            f"| {'yes' if item.dirty else 'no'} | {cell(item.reason)} |"
        )
    print()
    print("### Branches")
    print()
    print("| Category | Branch | Remote | vs remote | vs default | PR | State | Author | Reason |")
    print("|---|---|---|---|---|---:|---|---|---|")
    for item in branches:
        pr = f"[#{item.pr.number}]({item.pr.url})" if item.pr else "-"
        state = "merged" if item.pr and item.pr.merged else item.pr.state if item.pr else "-"
        author = f"@{item.pr.author}" if item.pr else "-"
        print(
            f"| {item.category} | `{cell(item.name)}` | `{cell(item.upstream)}` "
            f"| {cell(item.relation)} | {cell(item.default_relation)} | {pr} "
            f"| {state} | {author} | {cell(item.reason)} |"
        )
    print()


def scan(repo_path: str, fetch: bool, current_user: str) -> None:
    requested = Path(repo_path).expanduser().resolve()
    root = Path(run(["git", "rev-parse", "--show-toplevel"], requested))
    if fetch:
        run(["git", "fetch", "--prune", "origin"], root)
    owner, repo = github_repo(root)
    default = default_ref(root)
    worktrees = read_worktrees(root)
    prs = fetch_pull_requests(root, owner, repo)
    branches = read_branches(root, default, current_user, prs, worktrees)
    worktree_reports = classify_worktrees(root, default, worktrees)
    print_report(root, f"{owner}/{repo}", default, current_user, branches, worktree_reports)


def self_check() -> None:
    base = dict(
        name="topic",
        is_default=False,
        is_backup=False,
        checked_out=False,
        dirty_worktree=False,
        upstream_exists=True,
        remote_equal=True,
        ahead=0,
        in_default=False,
        merged_pr=False,
        pr=None,
        current_user="me",
    )

    def category(**changes: object) -> str:
        return classify_branch(BranchEvidence(**(base | changes)))[0]

    assert category(is_default=True) == "KEEP"
    assert category(is_backup=True) == "KEEP"
    assert category(dirty_worktree=True) == "BLOCKED"
    assert category(ahead=1, upstream_exists=False, remote_equal=False) == "KEEP"
    assert category(in_default=True) == "DELETE"
    assert category(in_default=True, checked_out=True) == "CONFIRM"
    assert category(pr=PullRequest(1, "closed", False, "me", "x", "u", "")) == "CONFIRM"
    assert category(pr=PullRequest(2, "open", False, "me", "x", "u", "")) == "KEEP"
    assert category(pr=PullRequest(3, "open", False, "other", "x", "u", "")) == "DELETE"
    old = PullRequest(4, "closed", True, "me", "old", "u", "2026-01-01")
    current = PullRequest(5, "open", False, "me", "current", "u", "2026-02-01")
    assert representative_pr([old, current]) == current
    worktree = dict(
        primary=False,
        locked=False,
        prunable=False,
        exists=True,
        dirty=False,
        detached=False,
        detached_in_default=False,
    )
    assert worktree_decision(**worktree)[0] == "DELETE"
    assert worktree_decision(**(worktree | {"detached": True}))[0] == "CONFIRM"
    assert worktree_decision(**(worktree | {"dirty": True}))[0] == "BLOCKED"
    print("self-check passed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify local Git branches and worktrees before cleanup."
    )
    parser.add_argument("repos", nargs="*", default=["."], metavar="REPO_PATH")
    parser.add_argument("--no-fetch", action="store_true", help="Use cached origin refs")
    parser.add_argument("--self-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.self_check:
        self_check()
        return 0

    try:
        current_user = run(["gh", "api", "user", "--jq", ".login"], Path.cwd())
        for repo in args.repos:
            scan(repo, not args.no_fetch, current_user)
    except (CommandError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
