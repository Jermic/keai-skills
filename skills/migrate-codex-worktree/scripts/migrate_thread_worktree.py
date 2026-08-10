#!/usr/bin/env python3
"""Migrate one Codex thread after its Git worktree path changes.

Fully quit the Codex GUI, then run:
    migrate_thread_worktree.py THREAD_ID OLD_PATH NEW_PATH

The migration backs up the SQLite database, global state, and rollout JSONL
before changing only active metadata for the selected thread. config.toml is
inspected but never changed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any


ROLLOUT_KEYS = {
    "cwd",
    "workspace_roots",
    "sandbox_policy",
    "permission_profile",
    "file_system_sandbox_policy",
}


class MigrationError(RuntimeError):
    pass


def replace_prefix(value: Any, old: str, new: str) -> tuple[Any, int]:
    """Replace a path only when it equals old or is below old."""
    if isinstance(value, str):
        if value == old or value.startswith(old + os.sep):
            return new + value[len(old) :], 1
        return value, 0
    if isinstance(value, list):
        result, changes = [], 0
        for item in value:
            updated, count = replace_prefix(item, old, new)
            result.append(updated)
            changes += count
        return result, changes
    if isinstance(value, dict):
        result, changes = {}, 0
        for key, item in value.items():
            updated, count = replace_prefix(item, old, new)
            result[key] = updated
            changes += count
        return result, changes
    return value, 0


def count_prefix(value: Any, path: str) -> int:
    return replace_prefix(value, path, path)[1]


def transform_rollout_text(text: str, old: str, new: str) -> tuple[str, int]:
    output: list[str] = []
    changes = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise MigrationError(f"Invalid rollout JSON on line {number}") from error
        if record.get("type") in {"session_meta", "turn_context"}:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                raise MigrationError(f"Invalid rollout metadata on line {number}")
            changed = False
            for key in ROLLOUT_KEYS & payload.keys():
                updated, count = replace_prefix(payload[key], old, new)
                if count:
                    payload[key] = updated
                    changes += count
                    changed = True
            if changed:
                newline = "\n" if line.endswith("\n") else ""
                line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + newline
        output.append(line)
    return "".join(output), changes


def load_thread(db_path: Path, thread_id: str) -> tuple[str, dict[str, Any], Path]:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT cwd, sandbox_policy, rollout_path FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()
    if row is None:
        raise MigrationError(f"Thread not found: {thread_id}")
    try:
        sandbox = json.loads(row[1])
    except json.JSONDecodeError as error:
        raise MigrationError("threads.sandbox_policy is not valid JSON") from error
    return row[0], sandbox, Path(row[2])


def prepare_global_state(
    path: Path, thread_id: str, old: str, new: str
) -> tuple[dict[str, Any], int]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MigrationError(f"Invalid JSON: {path}") from error

    roots_by_thread = state.get("thread-writable-roots")
    assignments = state.get("thread-project-assignments")
    if not isinstance(roots_by_thread, dict) or thread_id not in roots_by_thread:
        raise MigrationError("thread-writable-roots has no entry for this thread")
    if not isinstance(assignments, dict) or not isinstance(assignments.get(thread_id), dict):
        raise MigrationError("thread-project-assignments has no entry for this thread")

    roots_by_thread[thread_id], root_changes = replace_prefix(
        roots_by_thread[thread_id], old, new
    )
    assignment = assignments[thread_id]
    assignment["cwd"], cwd_changes = replace_prefix(assignment.get("cwd"), old, new)
    return state, root_changes + cwd_changes


def check_config(path: Path, old: str, new: str) -> None:
    if not path.exists():
        return
    header = re.compile(
        r'''^\s*\[\s*projects\s*\.\s*(?P<key>"(?:\\.|[^"\\])*"|'[^']*')\s*\]\s*(?:#.*)?$'''
    )
    projects: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = header.match(line)
        if match:
            key = match.group("key")
            projects.add(json.loads(key) if key.startswith('"') else key[1:-1])
        elif line.lstrip().startswith("[projects."):
            raise MigrationError(f"Unsupported config.toml project header on line {number}")
    if old in projects:
        detail = (
            "both OLD_PATH and NEW_PATH have entries"
            if new in projects
            else "OLD_PATH has an entry"
        )
        raise MigrationError(
            f"config.toml {detail}; move or merge that project identity manually "
            "before retrying"
        )


def require_stopped_codex() -> None:
    result = subprocess.run(
        ["pgrep", "-x", "Codex"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        raise MigrationError("Codex is still running; fully quit it before retrying")
    if result.returncode != 1:
        raise MigrationError("Could not determine whether Codex is running")


def require_git_worktree(path: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode or Path(result.stdout.strip()).resolve() != path.resolve():
        raise MigrationError(f"NEW_PATH is not a Git worktree root: {path}")


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def discover_gitdir_candidates(value: Any, old: str) -> set[Path]:
    marker = f"{os.sep}.git{os.sep}worktrees{os.sep}"
    candidates: set[Path] = set()
    for text in iter_strings(value):
        prefix, separator, suffix = text.partition(marker)
        if not separator or not suffix:
            continue
        admin_dir = Path(prefix + marker + suffix.split(os.sep, 1)[0])
        gitdir_file = admin_dir / "gitdir"
        if not gitdir_file.is_file():
            continue
        candidate = Path(gitdir_file.read_text(encoding="utf-8").strip()).parent
        if str(candidate) == old:
            continue
        try:
            require_git_worktree(candidate)
        except MigrationError:
            continue
        candidates.add(candidate)
    return candidates


def discover() -> None:
    thread_id = os.environ.get("CODEX_THREAD_ID")
    if not thread_id:
        raise MigrationError("CODEX_THREAD_ID is unavailable in this task")
    codex_dir = Path.home() / ".codex"
    cwd, sandbox, rollout_path = load_thread(codex_dir / "state_5.sqlite", thread_id)
    if Path(cwd).exists():
        raise MigrationError(f"Current working directory still exists: {cwd}")
    if not rollout_path.is_file():
        raise MigrationError(f"Rollout file does not exist: {rollout_path}")

    metadata: list[Any] = [sandbox]
    for number, line in enumerate(rollout_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise MigrationError(f"Invalid rollout JSON on line {number}") from error
        if record.get("type") in {"session_meta", "turn_context"}:
            metadata.append(record.get("payload"))

    candidates = discover_gitdir_candidates(metadata, cwd)
    if len(candidates) != 1:
        rendered = ", ".join(sorted(map(str, candidates))) or "none"
        raise MigrationError(f"Expected one moved Git worktree, found: {rendered}")
    new = str(candidates.pop())
    check_config(codex_dir / "config.toml", cwd, new)
    print(json.dumps({"thread_id": thread_id, "old_path": cwd, "new_path": new}))


def atomic_write(path: Path, content: str) -> None:
    mode = path.stat().st_mode
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def backup_sqlite(source: Path, destination: Path) -> None:
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)


def verify(
    db_path: Path,
    global_path: Path,
    rollout_path: Path,
    config_path: Path,
    thread_id: str,
    old: str,
    new: str,
) -> None:
    cwd, sandbox, stored_rollout = load_thread(db_path, thread_id)
    if cwd != new or stored_rollout != rollout_path or count_prefix(sandbox, old):
        raise MigrationError("SQLite verification failed")

    state, stale_global = prepare_global_state(global_path, thread_id, old, new)
    assignment = state["thread-project-assignments"][thread_id]
    roots = state["thread-writable-roots"][thread_id]
    if stale_global or assignment.get("cwd") != new or new not in roots:
        raise MigrationError("Global state verification failed")

    _, stale_rollout = transform_rollout_text(
        rollout_path.read_text(encoding="utf-8"), old, new
    )
    if stale_rollout:
        raise MigrationError("Rollout metadata verification failed")
    check_config(config_path, old, new)


def normalize_path(value: str, name: str) -> str:
    path = Path(os.path.expanduser(value))
    if not path.is_absolute():
        raise MigrationError(f"{name} must be absolute")
    return os.path.normpath(str(path))


def migrate(thread_id: str, old: str, new: str) -> None:
    try:
        uuid.UUID(thread_id)
    except ValueError as error:
        raise MigrationError(f"Invalid THREAD_ID: {thread_id}") from error
    old = normalize_path(old, "OLD_PATH")
    new = normalize_path(new, "NEW_PATH")
    if old == new:
        raise MigrationError("OLD_PATH and NEW_PATH must differ")

    codex_dir = Path.home() / ".codex"
    db_path = codex_dir / "state_5.sqlite"
    global_path = codex_dir / ".codex-global-state.json"
    config_path = codex_dir / "config.toml"
    for path in (db_path, global_path):
        if not path.is_file():
            raise MigrationError(f"Required file does not exist: {path}")

    require_stopped_codex()
    require_git_worktree(Path(new))
    check_config(config_path, old, new)
    cwd, sandbox, rollout_path = load_thread(db_path, thread_id)
    if cwd not in {old, new}:
        raise MigrationError(f"Unexpected thread cwd: {cwd}")
    if not rollout_path.is_file():
        raise MigrationError(f"Rollout file does not exist: {rollout_path}")

    updated_sandbox, sandbox_changes = replace_prefix(sandbox, old, new)
    cwd_changes = int(cwd == old)
    updated_global, global_changes = prepare_global_state(
        global_path, thread_id, old, new
    )
    updated_rollout, rollout_changes = transform_rollout_text(
        rollout_path.read_text(encoding="utf-8"), old, new
    )
    total_changes = cwd_changes + sandbox_changes + global_changes + rollout_changes
    if not total_changes:
        verify(db_path, global_path, rollout_path, config_path, thread_id, old, new)
        print("Active metadata already points to NEW_PATH. You can start Codex.")
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = codex_dir / "path-migration-backups" / f"{timestamp}-{thread_id[:8]}"
    backup_dir.mkdir(parents=True)
    backup_sqlite(db_path, backup_dir / db_path.name)
    shutil.copy2(global_path, backup_dir / global_path.name)
    shutil.copy2(rollout_path, backup_dir / rollout_path.name)

    try:
        if global_changes:
            atomic_write(
                global_path,
                json.dumps(updated_global, ensure_ascii=False, separators=(",", ":")),
            )
        if rollout_changes:
            atomic_write(rollout_path, updated_rollout)
        if cwd_changes or sandbox_changes:
            with sqlite3.connect(db_path) as connection:
                cursor = connection.execute(
                    "UPDATE threads SET cwd = ?, sandbox_policy = ? WHERE id = ?",
                    (
                        new,
                        json.dumps(updated_sandbox, ensure_ascii=False, separators=(",", ":")),
                        thread_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise MigrationError("Expected exactly one SQLite row to change")
        verify(db_path, global_path, rollout_path, config_path, thread_id, old, new)
    except Exception as error:
        raise MigrationError(f"{error}\nBackup: {backup_dir}") from error

    print(f"Backup: {backup_dir}")
    print("Migration verified. You can start Codex.")


def self_check() -> None:
    old, new = "/tmp/old-worktree", "/tmp/new-worktree"
    metadata = json.dumps(
        {"type": "session_meta", "payload": {"cwd": old}}, separators=(",", ":")
    ) + "\n"
    chat = json.dumps(
        {"type": "response_item", "payload": {"text": f"keep {old} here"}},
        separators=(",", ":"),
    ) + "\n"
    context = json.dumps(
        {
            "type": "turn_context",
            "payload": {
                "workspace_roots": [old],
                "permission_profile": {"path": old + "/.git"},
            },
        },
        separators=(",", ":"),
    ) + "\n"
    updated, changes = transform_rollout_text(metadata + chat + context, old, new)
    lines = updated.splitlines(keepends=True)
    assert changes == 3
    assert json.loads(lines[0])["payload"]["cwd"] == new
    assert lines[1] == chat
    assert old in lines[1]
    assert count_prefix(json.loads(lines[2])["payload"], old) == 0
    repo_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory() as temporary:
        admin_dir = Path(temporary) / "repo" / ".git" / "worktrees" / "moved"
        admin_dir.mkdir(parents=True)
        (admin_dir / "gitdir").write_text(str(repo_root / ".git"), encoding="utf-8")
        assert discover_gitdir_candidates({"path": str(admin_dir)}, old) == {repo_root}
    print("self-check passed")


def parse_args(argv: list[str]) -> argparse.Namespace | str | None:
    if argv == ["--self-check"]:
        return None
    if argv == ["--discover"]:
        return "discover"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("THREAD_ID", help="Codex thread/task UUID")
    parser.add_argument("OLD_PATH", help="Former absolute worktree path")
    parser.add_argument("NEW_PATH", help="Current absolute Git worktree path")
    parser.epilog = "Use --discover for read-only parameter discovery or --self-check for checks."
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    if args is None:
        self_check()
    elif args == "discover":
        discover()
    else:
        migrate(args.THREAD_ID, args.OLD_PATH, args.NEW_PATH)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MigrationError, OSError, sqlite3.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
