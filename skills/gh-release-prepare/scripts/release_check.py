#!/usr/bin/env python3
"""Release preflight and live verification; no remote writes or release mutations."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")
SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
RELEASE_REF = re.compile(r"refs/heads/release/((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))\Z")
PR_FIELDS = "number,url,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,isCrossRepository,mergedAt"


def command(repo, *args):
    result = subprocess.run(args, cwd=repo, text=True, capture_output=True, timeout=120, check=False)
    if result.returncode:
        # stderr may contain credential-bearing remote URLs; never put it in JSON.
        raise RuntimeError(f"{args[0]} {args[1]} failed with exit code {result.returncode}")
    return result.stdout.strip()


def version(value):
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError(f"invalid stable release version: {value}")
    return tuple(map(int, match.groups()))


def choose_versions(releases, previous, next_version):
    versions = sorted((version(v), v) for v in releases)
    if not versions:
        raise ValueError("no stable release branches found")
    if previous is None:
        candidates = versions if next_version is None else [item for item in versions if item[0] < version(next_version)]
        if not candidates:
            raise ValueError("no previous stable release below next version")
        previous = candidates[-1][1]
    if previous not in releases:
        raise ValueError(f"previous release branch does not exist: {previous}")
    if next_version is None:
        major, minor, patch = version(previous)
        next_version = f"{major}.{minor}.{patch + 1}"
    if version(next_version) <= version(previous):
        raise ValueError("next version must be greater than previous")
    return previous, next_version


def live_refs(repo):
    refs = {}
    for line in command(repo, "git", "ls-remote", "--heads", "origin").splitlines():
        sha, ref = line.split("\t", 1)
        refs[ref] = sha
    return refs


def fetched_refs(repo):
    refs = {}
    for line in command(repo, "git", "for-each-ref", "--format=%(objectname)%09%(refname)",
                        "refs/remotes/origin").splitlines():
        sha, ref = line.split("\t", 1)
        prefix = "refs/remotes/origin/"
        if ref.startswith(prefix) and ref != prefix + "HEAD":
            refs["refs/heads/" + ref[len(prefix):]] = sha
    return refs


def matching_prs(repo, head):
    data = json.loads(command(repo, "gh", "pr", "list", "--state", "all", "--head", head,
                              "--limit", "1000", "--json", PR_FIELDS))
    if len(data) >= 1000:
        raise RuntimeError("PR list reached the limit; inspect this head manually")
    # gh's head filter does not support owner:branch; a fork with the same name is not our head.
    return [pr for pr in data if pr["headRefName"] == head]


def observations(repo, feature, next_version):
    bump = f"chore/bump-version-{next_version}"
    with ThreadPoolExecutor(max_workers=3) as pool:
        remote_job = pool.submit(live_refs, repo)
        feature_job = pool.submit(matching_prs, repo, feature)
        bump_job = pool.submit(matching_prs, repo, bump)
        return remote_job.result(), feature_job.result(), bump_job.result()


def local_state(repo, feature, previous_sha):
    branch_result = subprocess.run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=repo,
                                   text=True, capture_output=True, check=False)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = command(repo, "git", "rev-parse", "HEAD")
    feature_ref = subprocess.run(["git", "rev-parse", "--verify", f"refs/heads/{feature}"], cwd=repo,
                                 text=True, capture_output=True, check=False)
    feature_sha = feature_ref.stdout.strip() if feature_ref.returncode == 0 else None
    status = command(repo, "git", "status", "--porcelain=v1", "--untracked-files=all")
    aligned = False
    if previous_sha and feature_sha:
        aligned = subprocess.run(["git", "merge-base", "--is-ancestor", previous_sha, feature_sha],
                                 cwd=repo, capture_output=True, check=False).returncode == 0
    return {"branch": branch, "headSha": head, "featureSha": feature_sha,
            "dirty": bool(status), "changedPathCount": len(status.splitlines()) if status else 0,
            "featureDescendsFromPrevious": aligned}


def fast_path_reasons(snapshot):
    remote, local, prs = snapshot["remote"], snapshot["local"], snapshot["prs"]
    target = f"release/{snapshot['next']}"
    reasons = []
    if not remote["previous"]:
        reasons.append("missing-previous-release")
    if remote["release"] not in (None, remote["previous"]):
        reasons.append("release-has-additional-history-or-moved")
    if local["dirty"]:
        reasons.append("dirty-worktree-needs-full-patch-audit")
    if local["branch"] != snapshot["feature"] or not local["featureSha"]:
        reasons.append("feature-not-current-local-branch")
    if local["headSha"] != local["featureSha"]:
        reasons.append("feature-head-changed")
    if not local["featureDescendsFromPrevious"]:
        reasons.append("feature-baseline-not-proven")
    if local["featureSha"] == remote["previous"]:
        reasons.append("feature-has-no-commit")
    if remote["feature"] and remote["feature"] != local["featureSha"]:
        reasons.append("remote-feature-differs-from-local")
    if remote["bump"]:
        reasons.append("existing-bump-branch-needs-audit")
    feature_prs = prs["feature"]
    if len(feature_prs) > 1 or any(pr["isCrossRepository"] for pr in feature_prs):
        reasons.append("ambiguous-feature-pr")
    elif feature_prs and not (feature_prs[0]["state"] == "OPEN" and
                              feature_prs[0]["baseRefName"] == target and
                              feature_prs[0]["baseRefOid"] == remote["release"] and
                              feature_prs[0]["headRefOid"] == remote["feature"] and
                              feature_prs[0]["isDraft"] == snapshot["draft"]):
        reasons.append("feature-pr-needs-recovery")
    if prs["bump"]:
        reasons.append("existing-bump-pr-needs-audit")
    return reasons


def preflight(repo, args):
    command(repo, "git", "fetch", "--prune", "origin")
    fetch_spec = subprocess.run(["git", "config", "--get-all", "remote.origin.fetch"], cwd=repo,
                                text=True, capture_output=True, check=False).stdout.strip()
    standard_fetch = fetch_spec in ("+refs/heads/*:refs/remotes/origin/*",
                                    "refs/heads/*:refs/remotes/origin/*")
    refs = fetched_refs(repo) if standard_fetch else live_refs(repo)
    releases = {m.group(1): sha for ref, sha in refs.items() if (m := RELEASE_REF.fullmatch(ref))}
    previous, next_version = choose_versions(releases, args.previous, args.next)
    with ThreadPoolExecutor(max_workers=2) as pool:
        feature_job = pool.submit(matching_prs, repo, args.feature)
        bump_job = pool.submit(matching_prs, repo, f"chore/bump-version-{next_version}")
        feature_prs, bump_prs = feature_job.result(), bump_job.result()
    selected = {name: refs.get(f"refs/heads/{branch}") for name, branch in {
        "previous": f"release/{previous}", "release": f"release/{next_version}",
        "feature": args.feature, "bump": f"chore/bump-version-{next_version}"}.items()}
    snapshot = {"schemaVersion": 1, "feature": args.feature, "previous": previous,
                "next": next_version, "versionSources": {
                    "previous": "supplied" if args.previous else "greatest-below-next" if args.next else "greatest-stable",
                    "next": "supplied" if args.next else "previous-patch"},
                "draft": args.draft, "remote": selected,
                "local": local_state(repo, args.feature, selected["previous"]),
                "prs": {"feature": feature_prs, "bump": bump_prs}}
    snapshot["fastPathReasons"] = fast_path_reasons(snapshot)
    snapshot["fastPathCandidate"] = not snapshot["fastPathReasons"]
    return snapshot


def verify(repo, args):
    refs, feature_prs, bump_prs = observations(repo, args.feature, args.next)
    expected = {"previous": args.expect_previous, "release": args.expect_release,
                "feature": args.expect_feature, "bump": args.expect_bump}
    actual = {name: refs.get(f"refs/heads/{branch}") for name, branch in {
        "previous": f"release/{args.previous}", "release": f"release/{args.next}", "feature": args.feature,
        "bump": f"chore/bump-version-{args.next}"}.items()}
    mismatches = [f"{name}-sha" for name in expected if actual[name] != expected[name]]
    prs = {}
    for name, number, found in (("feature", args.feature_pr, feature_prs), ("bump", args.bump_pr, bump_prs)):
        matches = [pr for pr in found if pr["number"] == number]
        prs[name] = matches[0] if len(matches) == 1 and len(found) == 1 else None
        pr = prs[name]
        if not pr or pr["state"] != "OPEN" or pr["isCrossRepository"] or pr["isDraft"] != args.draft or \
                pr["baseRefName"] != f"release/{args.next}" or pr["baseRefOid"] != actual["release"] or \
                pr["headRefOid"] != actual[name]:
            mismatches.append(f"{name}-pr")
    return {"schemaVersion": 1, "remote": actual, "prs": prs, "mismatches": mismatches,
            "verified": not mismatches}


def write_json(value, output):
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        destination = Path(output)
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    sys.stdout.write(data)


def self_check():
    releases = {"1.4.9": "a", "1.4.10": "b", "1.5.0": "c"}
    assert choose_versions(releases, None, None) == ("1.5.0", "1.5.1")
    assert choose_versions(releases, None, "1.5.0") == ("1.4.10", "1.5.0")
    with patch(__name__ + ".command", return_value="a\trefs/remotes/origin/HEAD\nb\trefs/remotes/origin/release/1.5.0"):
        assert fetched_refs("unused") == {"refs/heads/release/1.5.0": "b"}
    snapshot = {"feature": "feature/x", "next": "1.5.1", "draft": False, "remote":
                {"previous": "a", "release": "a", "feature": "b", "bump": None},
                "local": {"dirty": False, "branch": "feature/x", "headSha": "b", "featureSha": "b",
                          "featureDescendsFromPrevious": True},
                "prs": {"feature": [], "bump": []}}
    assert not fast_path_reasons(snapshot)
    snapshot["local"]["dirty"] = True
    assert "dirty-worktree-needs-full-patch-audit" in fast_path_reasons(snapshot)
    snapshot["local"]["dirty"] = False
    snapshot["remote"]["release"] = "moved"
    assert "release-has-additional-history-or-moved" in fast_path_reasons(snapshot)
    snapshot["remote"]["release"] = "a"
    snapshot["prs"]["feature"] = [{"state": "CLOSED", "baseRefName": "release/1.5.1",
                                   "baseRefOid": "a", "headRefOid": "b", "isDraft": False,
                                   "isCrossRepository": False}]
    assert "feature-pr-needs-recovery" in fast_path_reasons(snapshot)
    snapshot["prs"]["feature"][0]["state"] = "MERGED"
    assert "feature-pr-needs-recovery" in fast_path_reasons(snapshot)
    snapshot["prs"]["feature"] = []
    snapshot["remote"]["bump"] = "c"
    assert "existing-bump-branch-needs-audit" in fast_path_reasons(snapshot)
    snapshot["remote"]["bump"] = None
    snapshot["remote"]["feature"] = "moved"
    assert "remote-feature-differs-from-local" in fast_path_reasons(snapshot)

    refs = {f"refs/heads/{name}": sha for name, sha in {
        "release/1.5.0": "a", "release/1.5.1": "b", "feature/x": "c",
        "chore/bump-version-1.5.1": "d"}.items()}
    feature_pr = {"number": 1, "state": "OPEN", "isCrossRepository": False, "isDraft": False,
                  "baseRefName": "release/1.5.1", "baseRefOid": "b", "headRefOid": "c"}
    bump_pr = {**feature_pr, "number": 2, "headRefOid": "d"}
    args = SimpleNamespace(feature="feature/x", previous="1.5.0", next="1.5.1",
                           expect_previous="a", expect_release="b", expect_feature="c",
                           expect_bump="d", feature_pr=1, bump_pr=2, draft=False)
    with patch(__name__ + ".observations", return_value=(refs, [feature_pr], [bump_pr])):
        assert verify("unused", args)["verified"]
    with patch(__name__ + ".observations", return_value=(refs, [{**feature_pr, "baseRefOid": "moved"}], [bump_pr])):
        assert "feature-pr" in verify("unused", args)["mismatches"]
    with patch(__name__ + ".observations", return_value=(refs, [{**feature_pr, "state": "CLOSED"}], [bump_pr])):
        assert "feature-pr" in verify("unused", args)["mismatches"]
    with patch(__name__ + ".observations", return_value=(refs, [feature_pr, {**feature_pr, "number": 3}], [bump_pr])):
        assert "feature-pr" in verify("unused", args)["mismatches"]
    with patch(__name__ + ".observations", return_value=({**refs, "refs/heads/release/1.5.1": "moved"},
                                                           [feature_pr], [bump_pr])):
        assert "release-sha" in verify("unused", args)["mismatches"]
    with patch(__name__ + ".observations", return_value=({**refs, "refs/heads/release/1.5.0": "moved"},
                                                           [feature_pr], [bump_pr])):
        assert "previous-sha" in verify("unused", args)["mismatches"]

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "ledger.json"
        with patch("sys.stdout"):
            write_json({"schemaVersion": 1}, output)
            write_json({"schemaVersion": 2}, output)
        assert json.loads(output.read_text()) == {"schemaVersion": 2}
        assert output.stat().st_mode & 0o777 == 0o600

    preflight_refs = {"refs/heads/release/1.5.0": "a", "refs/heads/release/1.5.1": "a",
                      "refs/heads/feature/x": "b"}
    preflight_local = {"dirty": False, "branch": "feature/x", "headSha": "b", "featureSha": "b",
                       "featureDescendsFromPrevious": True}
    preflight_args = SimpleNamespace(feature="feature/x", previous=None, next="1.5.1",
                                     draft=False)
    with patch(__name__ + ".command", return_value="") as git_command, \
            patch(__name__ + ".fetched_refs", return_value=preflight_refs), \
            patch(__name__ + ".matching_prs", return_value=[]), \
            patch(__name__ + ".local_state", return_value=preflight_local), \
            patch(__name__ + ".subprocess.run", return_value=SimpleNamespace(stdout="+refs/heads/*:refs/remotes/origin/*")):
        result = preflight("unused", preflight_args)
        assert result["previous"] == "1.5.0" and result["fastPathCandidate"]
        git_command.assert_called_once_with("unused", "git", "fetch", "--prune", "origin")
    print("self-check passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="action")
    for name in ("preflight", "verify"):
        part = sub.add_parser(name)
        part.add_argument("--repo", default=".")
        part.add_argument("--feature", required=True)
        part.add_argument("--previous")
        part.add_argument("--next")
        part.add_argument("--draft", action="store_true")
        if name == "preflight":
            part.add_argument("--output")
        else:
            for field in ("previous", "release", "feature", "bump"):
                part.add_argument(f"--expect-{field}", required=True)
            part.add_argument("--feature-pr", type=int, required=True)
            part.add_argument("--bump-pr", type=int, required=True)
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return 0
    if not args.action:
        parser.error("choose preflight or verify")
    try:
        repo = Path(args.repo).resolve()
        command(repo, "git", "rev-parse", "--show-toplevel")
        command(repo, "git", "check-ref-format", "--branch", args.feature)
        if args.previous:
            version(args.previous)
        if args.next:
            version(args.next)
        if args.action == "verify":
            if not args.previous or not args.next:
                raise ValueError("verify requires --previous and --next")
            for name in ("previous", "release", "feature", "bump"):
                if not SHA.fullmatch(getattr(args, f"expect_{name}")):
                    raise ValueError(f"invalid expected {name} SHA")
            result = verify(repo, args)
            write_json(result, None)
            return 0 if result["verified"] else 2
        result = preflight(repo, args)
        write_json(result, args.output)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"release_check: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
