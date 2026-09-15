#!/usr/bin/env python3
"""Offline regression check: exact comment/thread routing and guarded mutations."""
import contextlib
import io
import json
from unittest.mock import patch

import fetch_unresolved_threads as reader
import reply_and_resolve_thread as writer


def rejected(action):
  try:
    action()
  except SystemExit:
    return
  raise AssertionError('Expected rejection')


def main():
  base = 'https://github.com/owner/repo/pull/12'
  # A fork checkout must use the base repository encoded in gh's PR URL.
  with patch.object(reader, 'repo_from_git', side_effect=AssertionError('Origin is not the PR target')), patch.object(reader, 'run', return_value=json.dumps({'url': base})) as run:
    assert reader.parse_ref(None) == reader.PullRequestRef('owner', 'repo', 12)
    run.assert_called_once_with(['gh', 'pr', 'view', '--json', 'url'])
  for url in (None, '', 'https://example.com/owner/repo/pull/12'):
    with patch.object(reader, 'run', return_value=json.dumps({'url': url})):
      rejected(lambda: reader.parse_ref(None))
  review = reader.parse_ref(base + '#discussion_r7')
  conversation = reader.parse_ref(base + '#issuecomment-8')
  assert review.comment_id == 7 and review.comment_kind == 'discussion_r'
  assert conversation.comment_id == 8 and conversation.comment_kind == 'issuecomment-'
  assert reader.parse_ref(base + '/files#discussion_r7') == review
  assert reader.parse_ref(base).comment_id is None
  for value in (base + '#unknown', 'https://evil.example/' + base, base + '/unexpected#discussion_r7'):
    rejected(lambda: reader.parse_ref(value))

  calls = []
  def comment_api(cmd):
    calls.append(cmd)
    endpoint = cmd[-1]
    if endpoint == 'repos/owner/repo/pulls/comments/7':
      return json.dumps({'id': 7, 'in_reply_to_id': 6, 'pull_request_url': 'https://api.github.com/repos/owner/repo/pulls/12'})
    if endpoint == 'repos/owner/repo/pulls/comments/6':
      return json.dumps({'id': 6, 'pull_request_url': 'https://api.github.com/repos/owner/repo/pulls/12'})
    if endpoint == 'repos/owner/repo/issues/comments/8':
      return json.dumps({'id': 8, 'issue_url': 'https://api.github.com/repos/owner/repo/issues/12'})
    raise AssertionError(f'Unexpected broad lookup: {cmd}')
  with patch.object(reader, 'run', side_effect=comment_api):
    result = reader.fetch(review)
    assert result['scope'] == 'comment' and result['comment']['id'] == 7
    assert result['parentComment']['id'] == 6 and not result['contextComplete']
    assert reader.fetch(conversation)['commentKind'] == 'conversation'
  assert len(calls) == 3
  with patch.object(reader, 'run', return_value=json.dumps({'id': 7, 'pull_request_url': 'https://api.github.com/repos/owner/other/pulls/12'})):
    rejected(lambda: reader.fetch(review))

  def comment(ident):
    return {'databaseId': str(ident), 'updatedAt': f'2026-09-{ident:02}T00:00:00Z', 'url': base + f'#discussion_r{ident}', 'pullRequest': {'number': 12, 'repository': {'nameWithOwner': 'owner/repo'}}}
  def thread_page(ident):
    return {'data': {'node': {'id': 'PRRT_one', 'isResolved': False, 'path': 'app.py', 'line': 1, 'originalLine': 1, 'comments': {'totalCount': 2, 'nodes': [comment(ident)]}}}}
  pages = '\n'.join(json.dumps(thread_page(i)) for i in (6, 7))
  with patch.object(reader, 'run', return_value=pages) as run:
    thread = reader.fetch_thread(review, 'PRRT_one')
    assert thread['commentCount'] == 2 and thread['latestComment']['databaseId'] == 7
    query = next(arg for arg in run.call_args.args[0] if arg.startswith('query='))
    assert 'node(id:$id)' in query and 'reviewThreads' not in query
    rejected(lambda: reader.fetch_thread(reader.PullRequestRef('owner', 'other', 12), 'PRRT_one'))
    rejected(lambda: reader.fetch_thread(reader.parse_ref(base + '#discussion_r9'), 'PRRT_one'))
    rejected(lambda: reader.fetch_thread(conversation, 'PRRT_one'))
  bad = thread_page(7)
  with patch.object(reader, 'run', return_value=json.dumps(bad)):
    rejected(lambda: reader.fetch_thread(review, 'PRRT_one'))

  # A plain PR keeps the complete unresolved-thread route, including pagination.
  def pr_page(ident, resolved):
    t = {'id': f'PRRT_{ident}', 'isResolved': resolved, 'comments': {'totalCount': 1, 'nodes': [comment(ident)]}}
    return {'data': {'repository': {'pullRequest': {'number': 12, 'reviewThreads': {'nodes': [t]}}}}}
  with patch.object(reader, 'run', return_value='\n'.join(json.dumps(pr_page(i, i == 6)) for i in (6, 7))):
    assert [t['id'] for t in reader.fetch(reader.parse_ref(base))['unresolvedThreads']] == ['PRRT_7']

  # Two PR pages and a 101-comment thread: only the long open thread needs another query.
  short_threads = [pr_page(i, False)['data']['repository']['pullRequest']['reviewThreads']['nodes'][0] for i in range(1, 101)]
  long_comments = [{**comment(i), 'updatedAt': '2026-09-15T00:00:00Z'} for i in range(101, 202)]
  long_comments[-1]['updatedAt'] = '2026-09-16T00:00:00Z'
  long_thread = {**thread_page(7)['data']['node'], 'id': 'PRRT_long', 'comments': {'totalCount': 101, 'nodes': long_comments[:100]}}
  closed = {**long_thread, 'id': 'PRRT_closed', 'isResolved': True}
  def pr_nodes(nodes):
    return {'data': {'repository': {'pullRequest': {'number': 12, 'reviewThreads': {'nodes': nodes}}}}}
  pr_pages = '\n'.join(json.dumps(pr_nodes(nodes)) for nodes in (short_threads, [long_thread, closed]))
  def long_pages(comments):
    return '\n'.join(json.dumps({'data': {'node': {**long_thread, 'comments': {'totalCount': 101, 'nodes': batch}}}}) for batch in (comments[:100], comments[100:]))
  with patch.object(reader, 'run', side_effect=[pr_pages, long_pages(long_comments)]) as run:
    result = reader.fetch(reader.parse_ref(base))['unresolvedThreads']
    assert len(result) == len({t['id'] for t in result}) == 101
    fetched = next(t for t in result if t['id'] == 'PRRT_long')
    assert fetched['commentCount'] == 101 and fetched['latestComment']['databaseId'] == 201
    assert [c['databaseId'] for c in fetched['comments']['nodes']] == list(range(101, 202))
    assert run.call_count == 2
    assert '--paginate' in run.call_args_list[0].args[0]
    assert '--paginate' in run.call_args_list[1].args[0]
    assert 'id=PRRT_long' in run.call_args_list[1].args[0]
  # A duplicate must not conceal a missing comment even when totalCount matches.
  for comments in (long_comments[:-1], long_comments[:-1] + [long_comments[0]]):
    with patch.object(reader, 'run', return_value=long_pages(comments)):
      rejected(lambda: reader.fetch_thread(reader.parse_ref(base), 'PRRT_long'))
  with patch.object(reader, 'run', return_value=pr_pages + '\n' + json.dumps(pr_nodes([short_threads[0]]))):
    rejected(lambda: reader.fetch(reader.parse_ref(base)))
  with patch.object(reader, 'run', side_effect=[pr_pages, json.dumps({'errors': [{'message': 'failed'}]})]):
    rejected(lambda: reader.fetch(reader.parse_ref(base)))

  argv = ['reply', base + '#discussion_r7', '--thread-id', 'PRRT_one', '--expect-comment-id', '7', '--body', 'Fixed.']
  resolved = {**thread, 'isResolved': True}
  responses = [json.dumps({'data': {'addPullRequestReviewThreadReply': {'comment': {'url': base + '#discussion_r10'}}}}), json.dumps({'data': {'resolveReviewThread': {'thread': {'isResolved': True}}}})]
  with patch('sys.argv', argv), patch.object(writer, 'fetch', side_effect=AssertionError('Full PR fetch forbidden')), patch.object(writer, 'fetch_thread', side_effect=[thread, resolved]) as read, patch.object(writer, 'run', side_effect=responses) as run, contextlib.redirect_stdout(io.StringIO()) as out:
    assert writer.main() == 0
    assert json.loads(out.getvalue())['isResolved']
    assert run.call_count == 2 and read.call_count == 2
    reply_cmd = run.call_args_list[0].args[0]
    assert 'threadId=PRRT_one' in reply_cmd and 'body=Fixed.' in reply_cmd
    assert any('addPullRequestReviewThreadReply' in arg for arg in reply_cmd)
    assert not any('/replies' in arg for arg in reply_cmd)
  for response in (json.dumps({'errors': [{'message': 'failed'}]}), '{}', 'invalid json'):
    with patch('sys.argv', argv), patch.object(writer, 'fetch_thread', return_value=thread), patch.object(writer, 'run', return_value=response) as mutate:
      rejected(writer.main)
      assert mutate.call_count == 1
  with patch('sys.argv', argv + ['--dry-run']), patch.object(writer, 'fetch_thread', return_value=thread), patch.object(writer, 'run') as mutate, contextlib.redirect_stdout(io.StringIO()):
    assert writer.main() == 0
    mutate.assert_not_called()
  without_expected = argv[:4] + argv[6:]
  with patch('sys.argv', without_expected), patch.object(writer, 'fetch_thread', return_value=thread), patch.object(writer, 'run') as mutate:
    rejected(writer.main)
    mutate.assert_not_called()
  stale = {**thread, 'latestComment': {'databaseId': 9}}
  for current in (stale, resolved):
    with patch('sys.argv', argv), patch.object(writer, 'fetch_thread', return_value=current), patch.object(writer, 'run') as mutate:
      rejected(writer.main)
      mutate.assert_not_called()
  with patch('sys.argv', ['reply', base + '#discussion_r7', '--index', '1', '--body', 'Fixed.']), patch.object(writer, 'fetch') as broad, patch.object(writer, 'run') as mutate:
    rejected(writer.main)
    broad.assert_not_called()
    mutate.assert_not_called()
  with patch('sys.argv', argv), patch.object(writer, 'fetch_thread', return_value=thread), patch.object(writer, 'run', side_effect=[responses[0], json.dumps({'errors': [{'message': 'failed'}]})]) as mutate:
    try:
      writer.main()
    except SystemExit as error:
      assert 'Reply posted:' in str(error) and 'Do not resend' in str(error)
    else:
      raise AssertionError('Resolution failure was reported as success')
    assert mutate.call_count == 2
  print('review scope checks passed')


if __name__ == '__main__':
  main()
