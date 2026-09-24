# Release preparation recovery paths

Read this file when preflight is not a fast-path candidate or when a remote/PR changes. Rebuild the preflight ledger after a failed fast path. Never infer safety from branch names or a prior run's SHA.

## Dirty feature and wrong baseline

Review staged, unstaged, and relevant untracked changes in full. A working-tree patch may be used directly only when feature HEAD equals `PREVIOUS_RELEASE_SHA`; it has no commit series for `range-diff`. Separate task hunks from unrelated work, request exact scope if ambiguous, stage only approved hunks, and inspect the staged patch. Preserve unrelated changes. If the feature branch is committed and misbased, record old feature SHA and patch base, rebase only its feature commits onto `PREVIOUS_RELEASE_SHA`, then compare `git range-diff <old-base>..<old-feature-sha> <previous-release-sha>..<new-feature-sha>`, changed-file lists, and complete old/new patches. Account for every difference before publishing.

## Release and bump reuse

For an existing `release/<next>`, prove `PREVIOUS_RELEASE_SHA` ancestry. List every commit in `PREVIOUS_RELEASE_SHA..origin/release/<next>`, map each to its PR or release purpose, and block on any unexplained commit. For an existing bump worktree/branch, verify checked-out branch, clean or understood task-local changes, baseline ancestry, and version-only diff. Retain its actual baseline; do not claim it was created from the current release tip. Record `BUMP_BASE_SHA`. If release moves, fetch its new tip, account for new commits, verify bump ancestry, and inspect the complete current PR diff before PR creation/mutation.

## Feature rewrite

Record fetched remote feature SHA as `OLD_FEATURE_SHA`. Re-check the live remote ref immediately before rewrite; request explicit approval for that exact old/new SHA pair. Use `git push --force-with-lease=refs/heads/<feature>:<OLD_FEATURE_SHA> origin <NEW_FEATURE_SHA>:refs/heads/<feature>`. If the remote moved, stop, fetch it, re-audit and request a new decision. A normal push is allowed only for a compatible fast-forward; never use `--force` alone.

## Merged, closed, or mismatched PR

For a merged feature PR, prove it is the expected feature by comparing changed files and patch content with the intended feature evidence. Record its head SHA, historical base/head, merged state, and audited release commit; then continue with the bump path. A deleted feature ref is not an error if this evidence is complete. A closed-unmerged PR is unresolved. For multiple matches or wrong base/head/Draft state, report all matches and seek the specific retarget/recreate choice; do not silently mutate them. Confirm the live base/head/OID/state immediately before any PR mutation and again afterward.
