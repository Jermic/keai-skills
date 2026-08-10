#!/usr/bin/env python3
"""Plan minimal, unique Notion Enhanced Markdown search/replace updates."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


CONTENT_RE = re.compile(r"<content(?:\s[^>]*)?>\s*\n?(.*?)\n?\s*</content>", re.DOTALL)
TABLE_DIVIDER_RE = re.compile(r"^:?-{3,}:?$")
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})([^\s`]*)")
XML_BLOCK_RE = re.compile(r"^\s*<(table|details|callout|columns|synced_block|synced_block_reference|meeting-notes)\b")
LANGUAGE_ALIASES = {
    "bash": "shell",
    "js": "javascript",
    "md": "markdown",
    "plaintext": "plain text",
    "py": "python",
    "rb": "ruby",
    "sh": "shell",
    "text": "plain text",
    "ts": "typescript",
    "txt": "plain text",
    "yml": "yaml",
    "zsh": "shell",
}


@dataclass(frozen=True)
class Block:
    raw: str
    start: int
    end: int


def extract_content(text: str) -> str:
    match = CONTENT_RE.search(text)
    return match.group(1) if match else text.strip()


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells: list[str] = []
    cell: list[str] = []
    escaped = False
    code_ticks = 0
    for char in line:
        if escaped:
            cell.append(char)
            escaped = False
        elif char == "\\":
            cell.append(char)
            escaped = True
        elif char == "`":
            code_ticks = 0 if code_ticks else 1
            cell.append(char)
        elif char == "|" and not code_ticks:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(char)
    cells.append("".join(cell).strip())
    return cells


def is_pipe_table(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or "|" not in lines[index]:
        return False
    header = split_table_row(lines[index])
    divider = split_table_row(lines[index + 1])
    return len(header) > 1 and len(header) == len(divider) and all(TABLE_DIVIDER_RE.fullmatch(cell) for cell in divider)


def table_to_notion(rows: list[list[str]]) -> list[str]:
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("pipe table rows must have the same number of cells")
    output = ['<table header-row="true">']
    for row in rows:
        output.append("\t<tr>")
        output.extend(f"\t\t<td>{html.escape(cell, quote=False)}</td>" for cell in row)
        output.append("\t</tr>")
    output.append("</table>")
    return output


def markdown_to_notion(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    output: list[str] = []
    index = 0
    fence: str | None = None
    while index < len(lines):
        line = lines[index]
        fence_match = FENCE_RE.match(line)
        if fence:
            output.append(line)
            if line.lstrip().startswith(fence):
                fence = None
            index += 1
            continue
        if fence_match:
            fence = fence_match.group(2)
            output.append(line)
            index += 1
            continue
        if is_pipe_table(lines, index):
            rows = [split_table_row(lines[index])]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(split_table_row(lines[index]))
                index += 1
            output.extend(table_to_notion(rows))
            continue
        output.append(line)
        index += 1
    return "\n".join(output).strip()


def tokenize(text: str) -> list[Block]:
    lines = text.splitlines(keepends=True)
    blocks: list[Block] = []
    offset = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        start = offset
        offset += len(line)
        index += 1
        if not line.strip():
            continue
        fence_match = FENCE_RE.match(line)
        xml_match = XML_BLOCK_RE.match(line)
        if fence_match:
            fence = fence_match.group(2)
            while index < len(lines):
                candidate = lines[index]
                offset += len(candidate)
                index += 1
                if candidate.lstrip().startswith(fence):
                    break
        elif line.strip() == "$$":
            while index < len(lines):
                candidate = lines[index]
                offset += len(candidate)
                index += 1
                if candidate.strip() == "$$":
                    break
        elif xml_match:
            tag = xml_match.group(1)
            closing = f"</{tag}>"
            depth = line.count(f"<{tag}") - line.count(closing)
            while depth > 0 and index < len(lines):
                candidate = lines[index]
                offset += len(candidate)
                index += 1
                depth += candidate.count(f"<{tag}") - candidate.count(closing)
        else:
            while index < len(lines) and lines[index][:1] in {"\t", " "} and lines[index].strip():
                offset += len(lines[index])
                index += 1
        raw = text[start:offset].rstrip("\r\n")
        blocks.append(Block(raw, start, start + len(raw)))
    return blocks


def normalize(block: str) -> str:
    text = block.replace("\r\n", "\n").replace("\r", "\n").strip()
    if FENCE_RE.match(text):
        lines = text.splitlines()
        match = FENCE_RE.match(lines[0])
        assert match
        language = LANGUAGE_ALIASES.get(match.group(3).lower(), match.group(3).lower())
        lines[0] = f"{match.group(2)}{language}"
        return "\n".join(lines)
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r'<span\b(?=[^>]*(?:discussion|data-discussion))[^>]*>(.*?)</span>', r"\1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\s*<colgroup>.*?</colgroup>\s*", "\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<table\b([^>]*)>", _normalize_table_tag, text, flags=re.IGNORECASE)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", _normalize_auto_link, text)
    lines = [re.sub(r"[ \t]+$", "", line).replace("    ", "\t") for line in text.splitlines()]
    return "\n".join(line for line in lines if line.strip()).strip()


def _normalize_table_tag(match: re.Match[str]) -> str:
    attrs = dict(re.findall(r'(header-row|header-column)="(true|false)"', match.group(1), re.IGNORECASE))
    kept = "".join(f' {key}="true"' for key in ("header-row", "header-column") if attrs.get(key) == "true")
    return f"<table{kept}>"


def _normalize_auto_link(match: re.Match[str]) -> str:
    label, target = match.groups()
    comparable = re.sub(r"^https?://", "", target, flags=re.IGNORECASE).rstrip("/")
    return label if label.rstrip("/") == comparable else match.group(0)


def exact_window(text: str, blocks: list[Block], start: int, end: int) -> str:
    return text[blocks[start].start : blocks[end - 1].end]


def render_window(blocks: list[Block], start: int, end: int) -> str:
    return "\n".join(block.raw for block in blocks[start:end])


def plan(current: str, source: str, preserve_prefix_blocks: int) -> dict[str, object]:
    current = extract_content(current)
    current_blocks = tokenize(current)
    if not 0 <= preserve_prefix_blocks <= len(current_blocks):
        raise ValueError("preserve-prefix-blocks exceeds current block count")
    converted = markdown_to_notion(source)
    source_blocks = tokenize(converted)
    target_blocks = current_blocks[:preserve_prefix_blocks] + source_blocks
    old_keys = [normalize(block.raw) for block in current_blocks]
    new_keys = [normalize(block.raw) for block in target_blocks]
    matcher = SequenceMatcher(None, old_keys, new_keys, autojunk=False)
    updates: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    windows: list[tuple[int, int]] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        left_old, right_old = old_start, old_end
        left_new, right_new = new_start, new_end
        if left_old == right_old:
            if left_old > 0 and left_new > 0:
                left_old -= 1
                left_new -= 1
            elif right_old < len(current_blocks) and right_new < len(target_blocks):
                right_old += 1
                right_new += 1
            else:
                raise ValueError("cannot anchor insertion into an empty page")
        old_str = exact_window(current, current_blocks, left_old, right_old)
        expand_left = True
        while current.count(old_str) != 1:
            can_left = left_old > 0 and left_new > 0 and old_keys[left_old - 1] == new_keys[left_new - 1]
            can_right = right_old < len(current_blocks) and right_new < len(target_blocks) and old_keys[right_old] == new_keys[right_new]
            if not can_left and not can_right:
                break
            if can_left and (expand_left or not can_right):
                left_old -= 1
                left_new -= 1
            else:
                right_old += 1
                right_new += 1
            expand_left = not expand_left
            old_str = exact_window(current, current_blocks, left_old, right_old)
        windows.append((left_old, right_old))
        unique = current.count(old_str) == 1
        checks.append(
            {
                "old_block_range": [left_old, right_old],
                "new_block_range": [left_new, right_new],
                "unique": unique,
            }
        )
        updates.append(
            {
                "old_str": old_str,
                "new_str": render_window(target_blocks, left_new, right_new),
                "replace_all_matches": False,
            }
        )
    overlaps = any(a_start < b_end and b_start < a_end for index, (a_start, a_end) in enumerate(windows) for b_start, b_end in windows[index + 1 :])
    matched = sum(size for _, _, size in matcher.get_matching_blocks())
    return {
        "current_blocks": len(current_blocks),
        "target_blocks": len(target_blocks),
        "matched_blocks": matched,
        "semantic_equal": old_keys == new_keys,
        "preserved_prefix_blocks": preserve_prefix_blocks,
        "overlapping_replacements": overlaps,
        "replacement_checks": checks,
        "content_updates": updates,
        "target": render_window(target_blocks, 0, len(target_blocks)),
    }


def self_check() -> None:
    source = "# Plan\n\n| Name | State |\n| --- | --- |\n| A | Ready |\n\n```mermaid\nA[\"User (A)\"] --> B\n```"
    converted = markdown_to_notion(source)
    assert '<table header-row="true">' in converted and "<td>Name</td>" in converted
    assert '```mermaid\nA["User (A)"] --> B\n```' in converted
    assert normalize('<span discussion-ids="x">user.talk</span>') == "user.talk"
    assert normalize('[user.talk](https://user.talk/)') == "user.talk"
    assert normalize('```py\nprint(1)\n```') == normalize('```python\nprint(1)\n```')
    assert normalize('<table header-row="true">\n<colgroup><col width="100"></colgroup>\n<tr><td>A</td></tr>\n</table>') == normalize('<table header-row="true">\n<tr><td>A</td></tr>\n</table>')
    result = plan("# First\nsame\n# Second\nsame", "# First\nchanged\n# Second\nsame", 0)
    assert result["replacement_checks"][0]["unique"] is True
    assert result["content_updates"][0]["old_str"] == "# First\nsame"
    print("self-check passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", nargs="?", type=Path)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--preserve-prefix-blocks", type=int)
    parser.add_argument("--target-out", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    if args.current is None or args.source is None or args.preserve_prefix_blocks is None:
        parser.error("current, source, and --preserve-prefix-blocks are required")
    result = plan(args.current.read_text(), args.source.read_text(), args.preserve_prefix_blocks)
    target = result.pop("target")
    if args.target_out:
        args.target_out.write_text(f"{target}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
