---
name: gh-release-prepare
description: "Use when preparing the next release as separate feature and version-bump PRs, or recovering and retargeting existing release work."
---

# GH Release Prepare

Prepare one `release/<next>` branch and two independent PRs: feature and version bump. Run one repository and one feature at a time. Preparation never includes merge, tag, deploy, release-back, or deletion; each needs separate authorization.

## 1. Resolve and preflight

Read the target repository's instructions and toolchain. Record the feature branch, target checkout, supplied previous/next versions, and requested Draft state (default Ready). Report the current branch and ask once about current checkout versus a new worktree unless already chosen. State source branch, target branch, and path before creating a worktree.

Run `python3 <skill_dir>/scripts/release_check.py preflight --repo <checkout> --feature <branch> [--previous <version>] [--next <version>] [--draft]`. Resolve `<skill_dir>` from this active `SKILL.md`, not a fixed installation path. The command performs one `git fetch --prune origin`, reads its remote-tracking refs, queries matching PRs, then prints a JSON ledger. `--output <path>` optionally saves the same nonsensitive ledger with an atomic replace. Never put credentials, environment variables, PR bodies, or full diffs in the ledger.

Report resolved versions and their source before writes; ask only if the request conflicts with live evidence or remains ambiguous. If previous is omitted and next is supplied, use the greatest stable release below next; if both are omitted, use the greatest stable release and increment its patch. A repeated run with an existing next release needs an explicit next version to avoid deriving the following release. Validate supplied versions and collisions against live refs and PRs.

Inspect `git status`, staged, unstaged, and relevant untracked content, `git worktree list --porcelain`, feature merge base and full patch, version source, lock root entry, and recent bump diff. Classify every intended branch/worktree as create, reuse, or blocked. Classify every matching open, closed, and merged PR; reuse only a unique matching open PR. List all proposed writes and any ambiguous or unrelated changes before proceeding. Audit content against exact base/head SHAs and checks against exact content/environment; reuse unchanged results, refresh affected ranges after movement.

The JSON `fastPathCandidate` is a routing hint, never an audit verdict. Use the fast path only when its reasons list is empty **and** complete patch ownership, version source, and branch/worktree collision audits pass. A dirty patch, wrong baseline, release history beyond the previous SHA, existing bump branch, closed/merged/ambiguous PR, rebase, retarget, rewrite, or remote drift goes through [recovery.md](references/recovery.md). Do not repair a failed fast path in place; rebuild the ledger and follow the complete path.

## 2. Establish and audit the branches

Record `PREVIOUS_RELEASE_SHA` from fetched `origin/release/<previous>`. Create `release/<next>` at exactly that SHA only when absent. Push it with `git push --force-with-lease=refs/heads/release/<next>: origin <PREVIOUS_RELEASE_SHA>:refs/heads/release/<next>` so a concurrently changed ref cannot be overwritten; an already existing ref at the same SHA may succeed as a no-op. Never use that lease to rewrite an existing release ref. Confirm the remote release SHA equals `PREVIOUS_RELEASE_SHA`, and report `created` only if this run actually created it. If reusing a release branch, prove previous SHA ancestry and account for every extra commit and its PR/release purpose. An already merged expected feature is valid only after changed-file and patch identity are proven; see [recovery.md](references/recovery.md).

For an aligned committed feature, preserve history. For a working-tree patch at previous SHA, inspect complete staged and unstaged diffs, separate task hunks from unrelated edits, stage only approved paths/hunks, inspect the complete staged diff, and preserve unrelated changes. For a misbased feature, follow the rebase and `range-diff` rules in [recovery.md](references/recovery.md). Run the smallest existing feature checks before commit or push; run `git diff --check` on the working patch or `git diff --check <base>...<feature-head>` for committed content. Classify content failures separately from authentication, network, permission, and cache failures. Repeat staged whitespace checking only if staging changed the checked patch.

Push a new feature ref with an empty expected-SHA lease (`--force-with-lease=refs/heads/<feature>:`), so a concurrently changed ref cannot be overwritten. For an existing compatible ref, use a normal fast-forward push only when needed. Rewriting an existing remote feature requires explicit approval and a ref-level `--force-with-lease` pinned to the observed old SHA; a moved ref requires fresh evidence and a new decision. See [recovery.md](references/recovery.md). Confirm the remote feature SHA after push.

Create or reuse the independent `chore/bump-version-<next>` branch/worktree from the audited release tip `BUMP_BASE_SHA`. Before reuse, verify its branch, task-local dirt, baseline ancestry, and complete version-only diff. If release moves, fetch its new tip, account for every new commit, and re-audit the bump PR diff. See [recovery.md](references/recovery.md).

Detect the repository's existing version source and toolchain. For an uv project with a static project version and `uv.lock`, use `uv version <next> --no-sync` (add `--package` for an identified workspace member); inspect all generated changes and require only project version and root-package lock version changes. For other toolchains, use the repository's existing safe version command or edit only its confirmed version fields. Do not assume Python or Node, add dependencies, or let a version command create a tag. Run the existing lock consistency check and `git diff --check`; stage only the permitted version fields, inspect the complete staged diff, commit, then push a new bump ref with an empty expected-SHA lease or an existing compatible ref with a normal fast-forward push. Confirm the remote bump SHA.

## 3. Create or reuse PRs

Before PR mutation, refresh live release, feature, and bump SHAs with one `git ls-remote --heads origin` and recheck matching PR base/head/OID/state. Audit the complete feature and bump PR diffs against the live release tip: only the intended functionality may appear in feature, and only the project version and required lock root-package version may appear in bump. Fetch only a changed ref or missing object and re-audit affected ranges. A read followed by a write is not atomic: a concurrent change or PR-create collision stops the fast path and requires a fresh classification. Never silently retarget or recreate a closed/merged PR.

Both PRs target `release/<next>`: feature head `<feature>`, bump head `chore/bump-version-<next>`. Reuse only a unique open PR with exact base/head/OID and requested Draft state. Retarget or recreate an existing PR only after the specific choice is authorized. Feature PR body summarizes functionality, errors/boundaries, and checks actually run; bump PR body states the version-only change and lock check. For PR reuse, retarget, or merged recovery, follow [recovery.md](references/recovery.md).

Reuse authorization already granted for these exact targets/actions. If the initial request did not authorize writes, present one scoped plan for normal branch/worktree creation, limited version edits, commits, ordinary pushes, and new PRs. Force-push, changing an existing PR, merge, tag, deploy, release-back, and deletion remain separate decisions. A materially changed target invalidates the prior plan.

## 4. Verify and report

Run `python3 <skill_dir>/scripts/release_check.py verify --repo <checkout> --feature <branch> --previous <version> --next <version> --expect-previous <sha> --expect-release <sha> --expect-feature <sha> --expect-bump <sha> --feature-pr <number> --bump-pr <number> [--draft]`. It checks live refs and matching PR fields without another unconditional fetch. A deleted merged feature ref is an explicit recovery case: verify its PR head and audited merge commit separately. Resolve any mismatch before claiming completion. Check current branch and `git status --short --branch` in every used worktree.

| Project | Release | Feature PR | Bump PR |
| --- | --- | --- | --- |
| `<project>` | `release/<next>` · `<release SHA>` | [#<number>](<url>) · `<feature SHA>` · `<state>` | [#<number>](<url>) · `<bump SHA>` · `<state>` |

Report feature/bump checks and environment gaps; verified PR base, head, Draft state, and live state; worktree clean/sync/deletion eligibility; and unperformed merge/tag/deploy/release-back/delete actions. Say `created` only for actions taken in this run, and `open` or `merged` only from live GitHub state. The workflow is complete when every SHA, PR field, release ancestry, and reused commit is reconciled with live evidence.

## Offline regression and timing

After changing this skill, run `python3 <skill_dir>/scripts/release_check.py --self-check` and `git diff --check`. For a real preparation, record tool batches, fetch count, `ls-remote` count, PR query count, and elapsed time from first preflight to final verification. Compare only the same scenario and network conditions; report observed values separately from the 20-batch, 3m47s 1.5.2 baseline. Never merge write operations into a hidden script merely to meet a batch target.
