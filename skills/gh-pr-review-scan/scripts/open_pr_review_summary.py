#!/usr/bin/env python3
"""Print a Markdown summary of PR review status across repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


SEARCH_QUERY = """
query($searchQuery:String!, $endCursor:String) {
  search(query:$searchQuery, type:ISSUE, first:100, after:$endCursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        url
        state
        isDraft
        comments { totalCount }
      }
    }
  }
}
"""

THREADS_QUERY = """
query($owner:String!, $name:String!, $number:Int!, $endCursor:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      reviewThreads(first:100, after:$endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          comments { totalCount }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class PullRequest:
    repo: str
    number: int
    title: str
    url: str
    state: str
    is_draft: bool
    conversation_comments: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Outputs a Markdown table of PRs authored by LOGIN, defaulting to "
            "the current gh-authenticated user and open/draft PRs only."
        )
    )
    parser.add_argument("repos", nargs="+", metavar="owner/repo")
    parser.add_argument("--author", help="GitHub login to query")
    parser.add_argument(
        "--all-states",
        action="store_true",
        help="Include closed and merged PRs instead of defaulting to open PRs",
    )
    return parser.parse_args()


def run_gh(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("error: gh CLI is not installed or not on PATH", file=sys.stderr)
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            print(exc.stderr, file=sys.stderr, end="")
        raise SystemExit(exc.returncode)

    return result.stdout


def parse_paginated_json(output: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    documents: list[dict[str, Any]] = []
    index = 0

    while index < len(output):
        while index < len(output) and output[index].isspace():
            index += 1
        if index >= len(output):
            break
        document, index = decoder.raw_decode(output, index)
        documents.append(document)

    return documents


def current_author() -> str:
    return run_gh(["api", "user", "--jq", ".login"]).strip()


def graphql_paginated(fields: list[str]) -> list[dict[str, Any]]:
    output = run_gh(["api", "graphql", "--paginate", *fields])
    return parse_paginated_json(output)


def fetch_pull_requests(repo: str, author: str, include_all_states: bool) -> list[PullRequest]:
    search_query = f"repo:{repo} is:pr author:{author}"
    if not include_all_states:
        search_query = f"{search_query} state:open"

    pages = graphql_paginated(
        [
            "-f",
            f"query={SEARCH_QUERY}",
            "-f",
            f"searchQuery={search_query}",
        ]
    )

    pull_requests: list[PullRequest] = []
    for page in pages:
        nodes = page.get("data", {}).get("search", {}).get("nodes", [])
        for node in nodes:
            if not node:
                continue
            pull_requests.append(
                PullRequest(
                    repo=repo,
                    number=int(node["number"]),
                    title=str(node["title"]),
                    url=str(node["url"]),
                    state=str(node["state"]),
                    is_draft=bool(node["isDraft"]),
                    conversation_comments=int(node["comments"]["totalCount"]),
                )
            )

    return pull_requests


def fetch_thread_stats(owner: str, name: str, number: int) -> tuple[int, int, int]:
    pages = graphql_paginated(
        [
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={number}",
            "-f",
            f"query={THREADS_QUERY}",
        ]
    )

    resolved = 0
    unresolved = 0
    review_comments = 0

    for page in pages:
        threads = (
            page.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
            .get("nodes", [])
        )
        for thread in threads:
            if thread.get("isResolved"):
                resolved += 1
            else:
                unresolved += 1
            review_comments += int(thread.get("comments", {}).get("totalCount", 0))

    return resolved, unresolved, review_comments


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def validate_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        print(f"error: repository must be owner/repo, got: {repo}", file=sys.stderr)
        raise SystemExit(2)

    owner, name = repo.split("/", 1)
    if not owner or not name:
        print(f"error: repository must be owner/repo, got: {repo}", file=sys.stderr)
        raise SystemExit(2)

    return owner, name


def print_summary(repos: list[str], author: str, include_all_states: bool) -> None:
    print("| Repo | PR | Status | Title | Comment Total | Resolved | Unresolved |")
    print("|---|---:|---|---|---:|---:|---:|")

    for repo in repos:
        owner, name = validate_repo(repo)
        pull_requests = fetch_pull_requests(repo, author, include_all_states)

        if not pull_requests:
            print(f"| [{repo}](https://github.com/{repo}) | - | - | No open/draft PR | - | - | - |")
            continue

        for pull_request in pull_requests:
            resolved, unresolved, review_comments = fetch_thread_stats(
                owner, name, pull_request.number
            )
            total_comments = pull_request.conversation_comments + review_comments
            status = "DRAFT" if pull_request.is_draft else pull_request.state
            title = escape_markdown_cell(pull_request.title)

            print(
                f"| [{repo}](https://github.com/{repo}) "
                f"| [#{pull_request.number}]({pull_request.url}) "
                f"| {status} "
                f"| {title} "
                f"| {total_comments} "
                f"| {resolved} "
                f"| {unresolved} |"
            )


def main() -> None:
    args = parse_args()
    author = args.author or current_author()
    print_summary(args.repos, author, args.all_states)


if __name__ == "__main__":
    main()
