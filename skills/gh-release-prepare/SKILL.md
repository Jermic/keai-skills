---
name: gh-release-prepare
description: "Use when preparing the next release as separate feature and version-bump PRs, when an existing feature branch needs rebasing onto the previous release, or when existing release PRs need retargeting to the next release."
---

# GH Release Prepare

Prepare one next-release branch and two independent PRs: one feature PR and one version-bump PR. Treat creation, remote rewriting, and PR mutation as separate authorization boundaries. Run one repository and one feature at a time; combine repositories only in the final report.

## 1. Resolve the request

Collect:

- feature branch;
- target repository and either the current checkout or a chosen worktree;
- previous and next versions when the user provides them.

Read the target repository's `AGENTS.md` and repository instructions before choosing commands. Report the current branch, then ask whether to use the current project or create a new worktree unless the user already chose one. If creating a worktree, state the source branch, target branch, and path before creation.

Mark omitted versions for live derivation in preflight. Default both PRs to Ready; record Draft only when the user requests it. Defer PR reuse, retarget, or creation choices to preflight, where matching PRs can be identified.

This step is complete when the feature branch, repository, workspace, supplied or omitted version state, and Ready/Draft defaults are recorded and the workspace follows the target repository's rules.

## 2. Build the preflight ledger

Run `git fetch --prune origin`. Enumerate live remote branches matching stable `origin/release/<major>.<minor>.<patch>` SemVer, parse their numeric components, and select the greatest SemVer. If previous is omitted, use that greatest version; if next is omitted, increment the resolved previous version's patch component. Report both resolved versions and their source before any write. Confirm that a supplied previous release exists, a supplied next version is valid and later, and every supplied value agrees with branch and PR collision evidence. Use neither string sorting nor remembered release state.

Then inspect:

- `git status --short --branch` and staged changes;
- complete staged, unstaged, and relevant untracked feature changes;
- `git worktree list --porcelain`;
- local and remote branches named `release/<next>`, `<feature>`, and `chore/bump-version-<next>`;
- the exact SHA of `origin/release/<previous>`;
- the feature HEAD, its merge base and ancestry with the previous release, and whether feature content exists only as a working-tree patch;
- open, closed, and merged PRs for the feature and bump heads;
- the base, head, state, and draft status of every matching PR;
- the repository toolchain, current project version source of truth, lock root-package version, and recent version-bump commit and diff.

Classify each intended branch and worktree as `create`, `reuse`, or `blocked`. Present collisions and dirty state before any write. For each matching PR, show its evidence and ask whether to reuse it, retarget it, or create a new PR; default to creating the intended PR when no match exists.

This step is complete when both versions and the previous-release SHA are resolved from live remote evidence; feature baseline, complete local diff, project version source, and lock root version are recorded; every branch, worktree, and matching PR has exactly one classification; every detected PR match has an explicit handling choice; and all proposed writes are listed.

## 3. Establish the release baseline

Resolve and record `PREVIOUS_RELEASE_SHA` from the fetched `origin/release/<previous>`.

- For first creation, create `release/<next>` at exactly `PREVIOUS_RELEASE_SHA`, push it, and verify local and remote equality.
- For an existing branch selected for reuse, prove that `PREVIOUS_RELEASE_SHA` is its ancestor. List every commit in `PREVIOUS_RELEASE_SHA..origin/release/<next>`, map each commit to its PR or release purpose, and confirm that all belong to this release. Treat an already-merged expected feature PR as valid audited progress and continue with the bump path.

This step is complete when a newly created remote release branch equals `PREVIOUS_RELEASE_SHA`, or a reused remote release branch descends from it and every additional commit and corresponding PR is accounted for with no unexpected commit.

## 4. Align the feature branch

If a candidate feature PR is already merged into `release/<next>`, prove that it is the expected feature by comparing its changed files and patch content with the intended feature evidence. Record its head SHA, merged state, and audited release commit, then continue to the bump branch. Treat an ambiguous identity as blocked pending user direction.

Otherwise, classify the feature state and complete exactly one path:

- **Working-tree patch:** When feature HEAD equals `PREVIOUS_RELEASE_SHA` and feature content is staged or unstaged rather than committed, review both diffs in full. Separate the current task from unrelated edits and preserve unrelated changes outside the commit. Request exact scope when task hunks cannot be distinguished. This path uses no `range-diff`.
- **Committed and aligned:** When feature commits already descend from `PREVIOUS_RELEASE_SHA`, preserve their history.
- **Committed and misbased:** Record the old feature SHA and patch base, rebase the feature commits onto `PREVIOUS_RELEASE_SHA`, and record the new SHA. Compare commit series with `git range-diff <old-base>..<old-state-sha> <previous-release-sha>..<new-feature-sha>`, then compare changed-file lists and both patch diffs. Account for every difference.

After feature content is final, run the smallest existing feature-related checks and `git diff --check` on the working diff or intended committed feature range, as applicable, before any feature commit or push. Classify permission, authentication, network, and cache failures as environment failures; classify assertion, compilation, lint, type, and content failures as content failures.

For a working-tree patch, stage only current-task paths or hunks, inspect the complete staged diff, run `git diff --staged --check`, and commit according to the repository's Git rules. Verify that unrelated staged and unstaged changes remain preserved.

Publish according to remote state:

- When no remote feature ref existed, use a normal first push.
- When the remote ref exists and history remains compatible, use a normal push only when needed.
- When the remote ref exists and rebasing rewrote it, record its fetched SHA as `OLD_FEATURE_SHA`, re-check that the remote still equals it, and request explicit rewrite approval. After approval, push with `git push --force-with-lease=refs/heads/<feature>:<old-feature-sha> origin <new-feature-sha>:refs/heads/<feature>`. If the remote moved, refresh the evidence and request a new decision.

This step is complete when the feature is verified as already merged, or its final commit series descends from `PREVIOUS_RELEASE_SHA`, contains only the intended feature patch, has recorded passing checks or an exact environment gap, preserves unrelated local changes, and matches the verified remote outcome for its publication path.

## 5. Prepare the independent version bump

Create an independent worktree whose path and `chore/bump-version-<next>` branch follow the target repository's naming rules. Refresh `origin/release/<next>`, confirm that its history still matches the Step 3 audit, and record its current tip as `BUMP_BASE_SHA`. Create the bump branch from that exact tip. On first release creation `BUMP_BASE_SHA` equals `PREVIOUS_RELEASE_SHA`; on recovery it may include audited merged feature commits.

Use the version-source and toolchain evidence recorded in Step 2. Apply the next version only to the project's own version source and required lock root-package entry. Review generated lock changes by field and section; keep dependency versions and resolution metadata unchanged.

After bump content is final, run the repository's existing lock consistency check and `git diff --check`. Then stage only the permitted version source and lock root-package changes, inspect the complete staged diff, run `git diff --staged --check`, and commit according to the repository's Git rules. Push normally and verify the remote bump SHA.

If `origin/release/<next>` moves after `BUMP_BASE_SHA` is recorded, fetch the new tip and re-verify bump ancestry and the complete PR diff before PR creation or mutation. Account for every new release commit rather than carrying the old audit forward.

This step is complete when the independent bump worktree and branch start from the audited `BUMP_BASE_SHA`; the committed diff contains only the project version source and required lock root-package version; dependency data is unchanged; lock and diff checks pass or have an exact environment gap; and local and remote bump SHAs match.

## 6. Audit the prepared branches

Before creating or changing PRs, inspect each open head's live remote range against `origin/release/<next>`; for an already-merged feature, inspect its live PR head and merge diff instead:

- Feature contains only the intended functionality and its recorded error or boundary handling.
- Bump contains only the project version and required lock root-package change.
- Every required feature, lock, and diff check has its exact command and result.

If the current release tip differs from `BUMP_BASE_SHA`, repeat the bump ancestry and complete PR-diff audit against the new tip before continuing.

This step is complete when both open ranges or merged-PR evidence contain only their intended changes, every check result is accounted for as pass, content failure, or environment gap, and the current release tip is reconciled with `BUMP_BASE_SHA`.

## 7. Create or retarget the two PRs

Use `release/<next>` as the base of both PRs:

| PR | Head | Base |
| --- | --- | --- |
| Feature | `<feature>` | `release/<next>` |
| Version bump | `chore/bump-version-<next>` | `release/<next>` |

Apply the Ready default or requested Draft state. Follow the matching-PR choice from Step 2: reuse it, present and perform the selected retarget, or create a distinct PR when GitHub permits it.

Write the feature PR body with a concise functionality summary, error and boundary handling, and the checks actually run. Write the bump PR body as a version-only change and include the lock consistency result.

Creating these PRs completes preparation only. Merging, tagging, deploying, merging the release back to the default branch, and deleting branches each require later explicit authorization.

This step is complete when each intended PR has the required body and is either open with the required base, head, and Ready/Draft state or already merged into `release/<next>` with its historical base and head verified. A merged feature PR plus an open bump PR is a valid recovery state; a closed-unmerged PR remains unresolved.

## 8. Verify and report

Fetch remote state again and verify:

- live remote SHAs for `release/<next>`, `<feature>`, and `chore/bump-version-<next>`; when a merged feature branch was deleted, report the missing ref and use the live PR head SHA as recovery evidence;
- `release/<next>` equals `PREVIOUS_RELEASE_SHA` when newly created, or descends from it with every additional release commit audited when reused;
- feature and bump ancestry from their recorded baselines, including reconciliation of the current release tip with `BUMP_BASE_SHA`;
- each PR's URL, base, head, open/closed/merged state, and Ready/Draft state;
- current branch and `git status --short --branch` in every used workspace.

Use this final summary table, localizing headers to the user's language when useful. Run each repository independently through this skill, then add one row per completed repository:

| Project | Release | Feature PR | Bump PR |
| --- | --- | --- | --- |
| `<project>` | `release/<next>` · `<release short SHA>` | [#<number>](<url>) · `<feature short SHA>` · `<state>` | [#<number>](<url>) · `<bump short SHA>` · `<state>` |

After the table, list only:

- each project's feature and bump validation results;
- pytest or environment gaps, when present;
- each worktree's clean, sync, and deletion eligibility;
- the boundary that merge, tag, deploy, release-back, and branch or worktree deletion were not executed.

Report `created` only as an action taken during this run; report `open` and `merged` only as live GitHub states. Include verified PR base, head, and draft status in each project's validation results. The workflow is complete when every table SHA and PR field matches live remote state, each intended PR is precisely reported as open, merged, or unresolved, release ancestry and reused history are fully audited, every worktree is accounted for, and all later release actions remain outside the claimed result.
