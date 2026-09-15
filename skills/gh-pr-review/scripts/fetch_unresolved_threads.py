#!/usr/bin/env python3
"""Fetch unresolved GitHub PR review threads with gh GraphQL."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


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
              databaseId: fullDatabaseId
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
  comment_kind: str | None = None
  comment_id: int | None = None


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
  if len({thread["id"] for thread in threads}) != len(threads):
    raise SystemExit("Duplicate review threads across pages; retry the fetch.")
  return threads


def complete_comments(thread: dict[str, Any]) -> list[dict[str, Any]]:
  connection = thread["comments"]
  comments = connection["nodes"]
  if connection["totalCount"] != len(comments):
    raise SystemExit(f"Incomplete comments for review thread {thread['id']}.")
  if len({int(comment["databaseId"]) for comment in comments}) != len(comments):
    raise SystemExit(f"Duplicate comments for review thread {thread['id']}; retry the fetch.")
  return comments


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
  data = json.loads(run(["gh", "pr", "view", "--json", "url"]))
  url = data.get("url")
  if not isinstance(url, str) or not url.startswith("https://github.com/"):
    raise SystemExit("GitHub did not return a supported PR URL.")
  return parse_ref(url)


def parse_ref(value: str | None) -> PullRequestRef:
  if not value:
    return infer_current_pr()

  value = value.strip()

  url = urlsplit(value)
  url_match = re.fullmatch(
    r"/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)(?:/(?:files|commits))?/?",
    url.path,
  ) if url.scheme == "https" and url.netloc == "github.com" else None
  if url_match:
    anchor = re.fullmatch(r"(discussion_r|issuecomment-)(\d+)", url.fragment)
    if url.fragment and not anchor:
      raise SystemExit("Unsupported PR anchor; provide a comment permalink or a plain PR URL.")
    return PullRequestRef(
      owner=url_match.group("owner"),
      repo=url_match.group("repo"),
      number=int(url_match.group("number")),
      comment_kind=anchor.group(1) if anchor else None,
      comment_id=int(anchor.group(2)) if anchor else None,
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
  if pr.comment_id is not None:
    return fetch_comment(pr)
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
  if any(page.get("errors") for page in pages):
    raise SystemExit("GitHub returned GraphQL errors; refusing partial results.")

  data = pages[0]["data"]["repository"]["pullRequest"]
  if data is None:
    raise SystemExit(f"Pull request not found: {pr.owner}/{pr.repo}#{pr.number}")

  threads = [thread for thread in collect_threads(pages) if not thread["isResolved"]]
  for thread in threads:
    if thread["comments"]["totalCount"] > len(thread["comments"]["nodes"]):
      thread.update(fetch_thread(pr, thread["id"]))
    comments = complete_comments(thread)
    for comment in comments:
      comment["databaseId"] = int(comment["databaseId"])
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


def fetch_comment(pr: PullRequestRef) -> dict:
  """Fetch only the supplied comment, plus its parent when it is a reply."""
  collection = "pulls/comments" if pr.comment_kind == "discussion_r" else "issues/comments"

  def read_comment(comment_id: int) -> dict:
    comment = json.loads(run(["gh", "api", f"repos/{pr.owner}/{pr.repo}/{collection}/{comment_id}"]))
    expected = f"https://api.github.com/repos/{pr.owner}/{pr.repo}/" + (
      f"pulls/{pr.number}" if pr.comment_kind == "discussion_r" else f"issues/{pr.number}"
    )
    actual = comment.get("pull_request_url" if pr.comment_kind == "discussion_r" else "issue_url", "")
    if actual.casefold() != expected.casefold() or comment.get("id") != comment_id:
      raise SystemExit("Comment does not belong to the supplied PR; no scope expansion performed.")
    return comment

  comment = read_comment(pr.comment_id)
  parent_id = comment.get("in_reply_to_id")
  return {
    "scope": "comment",
    "number": pr.number,
    "url": f"https://github.com/{pr.owner}/{pr.repo}/pull/{pr.number}",
    "commentKind": "review" if pr.comment_kind == "discussion_r" else "conversation",
    "comment": comment,
    "parentComment": read_comment(parent_id) if parent_id else None,
    "contextComplete": False,
    "contextNote": "Only the linked comment and its parent are fetched; sibling replies and review-thread resolution state are not included.",
  }


def fetch_thread(pr: PullRequestRef, thread_id: str) -> dict:
  """Read one known thread by node ID, never enumerate the PR's threads."""
  query = """
  query($id:ID!, $endCursor:String) {
    node(id:$id) {
      ... on PullRequestReviewThread {
        id isResolved isOutdated path line originalLine
        comments(first:100, after:$endCursor) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes {
            databaseId: fullDatabaseId url body createdAt updatedAt
            author { login }
            pullRequest { number repository { nameWithOwner } }
          }
        }
      }
    }
  }
  """
  pages = parse_paginated_json(run([
    "gh", "api", "graphql", "--paginate", "-f", f"id={thread_id}", "-f", f"query={query}",
  ]))
  if not pages or any(page.get("errors") or not page.get("data", {}).get("node") for page in pages):
    raise SystemExit("Review thread not found or incomplete GraphQL response.")
  thread = pages[0]["data"]["node"]
  comments = [c for page in pages for c in page["data"]["node"]["comments"]["nodes"]]
  if any(page["data"]["node"]["id"] != thread_id for page in pages):
    raise SystemExit("Unexpected review thread in paginated response.")
  if not comments:
    raise SystemExit("Incomplete review thread comments.")
  thread["comments"]["nodes"] = comments
  complete_comments(thread)
  for comment in comments:
    owner_pr = comment["pullRequest"]
    if owner_pr["number"] != pr.number or owner_pr["repository"]["nameWithOwner"].casefold() != f"{pr.owner}/{pr.repo}".casefold():
      raise SystemExit("Thread does not belong to the supplied PR.")
    comment["databaseId"] = int(comment["databaseId"])
  if pr.comment_id is not None and (pr.comment_kind != "discussion_r" or not any(c["databaseId"] == pr.comment_id for c in comments)):
    raise SystemExit("Supplied comment is not part of the selected review thread.")
  thread["comments"]["nodes"] = comments
  thread["commentCount"] = len(comments)
  thread["latestComment"] = max(comments, key=lambda c: c["updatedAt"])
  thread["latestCommentAt"] = thread["latestComment"]["updatedAt"]
  return thread


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
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("target", nargs="?", help="PR reference or a specific comment permalink.")
  parser.add_argument("--thread-id", help="Read only this known review thread, including resolved state.")
  args = parser.parse_args()
  pr = parse_ref(args.target)
  result = fetch_thread(pr, args.thread_id) if args.thread_id else fetch(pr)
  json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
  sys.stdout.write("\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
