#!/usr/bin/env python3
"""Fetch unresolved GitHub PR review threads with gh GraphQL."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass


QUERY = """
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      number
      title
      url
      reviewDecision
      mergeStateStatus
      reviewThreads(first:100) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          startLine
          originalStartLine
          comments(first:30) {
            nodes {
              databaseId
              url
              body
              createdAt
              updatedAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""


@dataclass
class PullRequestRef:
  owner: str
  repo: str
  number: int


def run(cmd: list[str]) -> str:
  return subprocess.check_output(cmd, text=True).strip()


def repo_from_git() -> tuple[str, str]:
  remote = run(["git", "remote", "get-url", "origin"])
  patterns = [
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
  ]
  for pattern in patterns:
    match = re.search(pattern, remote)
    if match:
      return match.group("owner"), match.group("repo")
  raise SystemExit(f"Cannot parse GitHub origin remote: {remote}")


def infer_current_pr() -> PullRequestRef:
  owner, repo = repo_from_git()
  raw = run(["gh", "pr", "view", "--json", "number,url"])
  data = json.loads(raw)
  return PullRequestRef(owner=owner, repo=repo, number=int(data["number"]))


def parse_ref(value: str | None) -> PullRequestRef:
  if not value:
    return infer_current_pr()

  value = value.strip()

  url_match = re.search(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    value,
  )
  if url_match:
    return PullRequestRef(
      owner=url_match.group("owner"),
      repo=url_match.group("repo"),
      number=int(url_match.group("number")),
    )

  shorthand_match = re.fullmatch(
    r"(?:(?P<owner>[^/\s#]+)/(?P<repo>[^\s#]+))?#(?P<number>\d+)",
    value,
  )
  if shorthand_match:
    owner = shorthand_match.group("owner")
    repo = shorthand_match.group("repo")
    if not owner or not repo:
      owner, repo = repo_from_git()
    return PullRequestRef(owner=owner, repo=repo, number=int(shorthand_match.group("number")))

  owner_repo_match = re.fullmatch(
    r"(?P<owner>[^/\s#]+)/(?P<repo>[^\s#]+)#(?P<number>\d+)",
    value,
  )
  if owner_repo_match:
    return PullRequestRef(
      owner=owner_repo_match.group("owner"),
      repo=owner_repo_match.group("repo"),
      number=int(owner_repo_match.group("number")),
    )

  if value.isdigit():
    owner, repo = repo_from_git()
    return PullRequestRef(owner=owner, repo=repo, number=int(value))

  raise SystemExit(
    "PR must be a GitHub PR URL, owner/repo#number, #number, number, or omitted."
  )


def fetch(pr: PullRequestRef) -> dict:
  raw = run(
    [
      "gh",
      "api",
      "graphql",
      "-F",
      f"owner={pr.owner}",
      "-F",
      f"name={pr.repo}",
      "-F",
      f"number={pr.number}",
      "-f",
      f"query={QUERY}",
    ]
  )
  data = json.loads(raw)["data"]["repository"]["pullRequest"]
  threads = data["reviewThreads"]["nodes"]
  for thread in threads:
    comments = thread["comments"]["nodes"]
    latest_comment = max(comments, key=lambda comment: comment["updatedAt"]) if comments else None
    thread["commentCount"] = len(comments)
    thread["latestCommentAt"] = latest_comment["updatedAt"] if latest_comment else None
    thread["latestComment"] = latest_comment
  data["unresolvedThreads"] = [thread for thread in threads if not thread["isResolved"]]
  data["unresolvedThreads"].sort(
    key=lambda thread: thread["latestCommentAt"] or "",
    reverse=True,
  )
  del data["reviewThreads"]
  return data


def main() -> int:
  pr = parse_ref(sys.argv[1] if len(sys.argv) > 1 else None)
  result = fetch(pr)
  json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
  sys.stdout.write("\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
