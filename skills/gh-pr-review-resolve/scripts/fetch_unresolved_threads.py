#!/usr/bin/env python3
"""Fetch unresolved GitHub PR review threads with gh GraphQL."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


QUERY = """
query($owner:String!, $name:String!, $number:Int!, $endCursor:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      number
      title
      url
      reviewDecision
      mergeStateStatus
      reviewThreads(first:100, after:$endCursor) {
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
          comments(first:100) {
            totalCount
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


def parse_paginated_json(output: str) -> list[dict[str, Any]]:
  decoder = json.JSONDecoder()
  documents: list[dict[str, Any]] = []
  index = 0
  while index < len(output):
    while index < len(output) and output[index].isspace():
      index += 1
    if index < len(output):
      document, index = decoder.raw_decode(output, index)
      documents.append(document)
  return documents


def collect_threads(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
  threads = []
  for page in pages:
    page_pr = page["data"]["repository"]["pullRequest"]
    threads.extend(page_pr["reviewThreads"]["nodes"])
  return threads


def complete_comments(thread: dict[str, Any]) -> list[dict[str, Any]]:
  connection = thread["comments"]
  if connection["totalCount"] > len(connection["nodes"]):
    raise SystemExit(
      f"Review thread {thread['id']} has more than 100 comments; "
      "refusing to return a truncated result."
    )
  return connection["nodes"]


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
      "--paginate",
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
  pages = parse_paginated_json(raw)
  if not pages:
    raise SystemExit("GitHub returned no GraphQL pages.")

  data = pages[0]["data"]["repository"]["pullRequest"]
  if data is None:
    raise SystemExit(f"Pull request not found: {pr.owner}/{pr.repo}#{pr.number}")

  threads = collect_threads(pages)
  for thread in threads:
    comments = complete_comments(thread)
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


def self_check() -> int:
  documents = parse_paginated_json('{"page":1}\n{"page":2}\n')
  assert documents == [{"page": 1}, {"page": 2}]
  assert parse_ref("owner/repo#12") == PullRequestRef("owner", "repo", 12)
  pages = [
    {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"id": "one"}]}}}}},
    {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"id": "two"}]}}}}},
  ]
  assert [thread["id"] for thread in collect_threads(pages)] == ["one", "two"]
  try:
    complete_comments({"id": "long", "comments": {"totalCount": 2, "nodes": [{}]}})
  except SystemExit:
    pass
  else:
    raise AssertionError("truncated comments were accepted")
  print("self-check passed")
  return 0


def main() -> int:
  if sys.argv[1:] == ["--self-check"]:
    return self_check()
  pr = parse_ref(sys.argv[1] if len(sys.argv) > 1 else None)
  result = fetch(pr)
  json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
  sys.stdout.write("\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
