#!/usr/bin/env python3
"""Reply to a verified PR review thread and resolve it."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from fetch_unresolved_threads import fetch, fetch_thread, parse_ref


REPLY_MUTATION = """
mutation($threadId:ID!, $body:String!) {
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId, body:$body}) {
    comment { url }
  }
}
"""


RESOLVE_MUTATION = """
mutation($threadId:ID!) {
  resolveReviewThread(input:{threadId:$threadId}) {
    thread {
      id
      isResolved
    }
  }
}
"""


def run(cmd: list[str]) -> str:
  return subprocess.check_output(cmd, text=True).strip()


def read_body(args: argparse.Namespace) -> str:
  if args.body and args.body_file:
    raise SystemExit("Provide exactly one reply body via --body, --body-file, or stdin.")

  if args.body:
    body = args.body
  elif args.body_file:
    body = Path(args.body_file).read_text()
  elif not sys.stdin.isatty():
    body = sys.stdin.read()
  else:
    raise SystemExit("Provide exactly one reply body via --body, --body-file, or stdin.")

  body = body.strip()
  if not body:
    raise SystemExit("Reply body cannot be empty.")
  return body


def main() -> int:
  parser = argparse.ArgumentParser(
    description=__doc__,
  )
  parser.add_argument(
    "pr",
    nargs="?",
    help="PR reference or comment permalink; omit to infer the current PR.",
  )
  parser.add_argument(
    "--index",
    "-i",
    type=int,
    help="1-based unresolved thread number from fetch_unresolved_threads.py output order.",
  )
  parser.add_argument(
    "--thread-id",
    help="Exact GitHub review thread GraphQL id from fetch_unresolved_threads.py.",
  )
  parser.add_argument(
    "--expect-comment-id",
    type=int,
    help="Abort unless the selected thread's latest review comment database id matches.",
  )
  parser.add_argument("--body", help="Markdown reply body.")
  parser.add_argument("--body-file", help="Path to a Markdown reply body file.")
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print the selected thread and reply without sending or resolving.",
  )
  args = parser.parse_args()

  if bool(args.index) == bool(args.thread_id):
    raise SystemExit("Provide exactly one selector: --index or --thread-id.")
  if args.index is not None and args.index < 1:
    raise SystemExit("--index must be 1 or greater.")

  pr = parse_ref(args.pr)
  body = read_body(args)
  if pr.comment_id is not None and not args.thread_id:
    raise SystemExit("A comment permalink requires its known --thread-id to resolve; no full-PR lookup is performed.")
  if args.thread_id:
    thread = fetch_thread(pr, args.thread_id)
    if thread["isResolved"]:
      raise SystemExit("Thread is already resolved; no reply sent.")
    number = None
  else:
    threads = fetch(pr)["unresolvedThreads"]
    if args.index > len(threads):
      raise SystemExit(
        f"Thread index {args.index} is out of range; PR has {len(threads)} unresolved thread(s)."
      )
    thread = threads[args.index - 1]
    number = args.index
  latest = thread.get("latestComment") or {}
  if (args.expect_comment_id is not None and
      latest.get("databaseId") != args.expect_comment_id):
    raise SystemExit(
      "Selected thread latest comment id changed: "
      f"expected {args.expect_comment_id}, got {latest.get('databaseId')}."
    )
  selected = {
    "number": number,
    "threadId": thread["id"],
    "latestCommentId": latest.get("databaseId"),
    "path": thread["path"],
    "line": thread["line"] or thread["originalLine"],
    "latestCommentAt": thread["latestCommentAt"],
    "latestCommentUrl": latest.get("url"),
    "replyBody": body,
  }

  if args.dry_run:
    json.dump(selected, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0

  if args.expect_comment_id is None:
    raise SystemExit("Live actions require --expect-comment-id from the inspected thread.")

  if not latest.get("databaseId"):
    raise SystemExit("Selected thread has no latest review comment databaseId to reply to.")

  try:
    reply_raw = run([
      "gh", "api", "graphql", "-f", f"threadId={thread['id']}",
      "-f", f"body={body}", "-f", f"query={REPLY_MUTATION}",
    ])
    reply_response = json.loads(reply_raw)
    if reply_response.get("errors"):
      raise RuntimeError("GitHub returned a reply error")
    reply_url = reply_response["data"]["addPullRequestReviewThreadReply"]["comment"]["url"]
    if not reply_url:
      raise RuntimeError("GitHub did not return the reply URL")
  except (subprocess.CalledProcessError, RuntimeError, KeyError, ValueError, TypeError) as error:
    raise SystemExit(f"Reply not verified: {error}. Inspect this thread before retrying; resolution was not attempted.") from error
  try:
    resolve_raw = run([
      "gh",
      "api",
      "graphql",
      "-F",
      f"threadId={thread['id']}",
      "-f",
      f"query={RESOLVE_MUTATION}",
    ])
    response = json.loads(resolve_raw)
    if response.get("errors"):
      raise RuntimeError("GitHub returned a resolution error")
    resolve_result = response["data"]
    if not resolve_result["resolveReviewThread"]["thread"]["isResolved"]:
      raise RuntimeError("GitHub did not confirm resolution")
    if not fetch_thread(pr, thread["id"])["isResolved"]:
      raise RuntimeError("Live thread remains unresolved")
  except (subprocess.CalledProcessError, RuntimeError, KeyError, ValueError, SystemExit) as error:
    raise SystemExit(f"Reply posted: {reply_url}; resolution not verified: {error}. Do not resend the reply; inspect this thread and retry resolution only.") from error
  output = {
    **selected,
    "replyUrl": reply_url,
    "isResolved": resolve_result["resolveReviewThread"]["thread"]["isResolved"],
  }
  json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
  sys.stdout.write("\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
