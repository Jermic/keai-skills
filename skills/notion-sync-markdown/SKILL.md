---
name: notion-sync-markdown
description: "Use when the user wants to sync a local Markdown source of truth into an existing Notion page while preserving unchanged blocks and their IDs, child objects, and existing discussions."
---

# Notion Sync Markdown

Treat local Markdown as the only source of truth. Use any `.notion.md` file only to understand the old page; never merge it back into the source.

## Safe Workflow

1. Locate the original page with Notion search and fetch it with `include_discussions=true`. Do not create a replacement page.
2. Back up all discussions with `get_comments(include_all_blocks=true, include_resolved=true)` before any write. Keep the full thread text, authors, timestamps, resolved state, discussion IDs, and block anchors.
3. Read `notion://docs/enhanced-markdown-spec` in the current run. The format and tool surface can change; do not rely on remembered syntax.
4. Extract only the fetched `<content>`. Identify leading `<unknown>`, `<page>`, `<database>`, `<folder>`, synced, meeting-note, or other external-object blocks that are absent from the local source. Preserve those blocks verbatim and record their count.
5. Resolve `<skill_dir>` to this skill directory and generate a dry-run plan:

```bash
python3 <skill_dir>/scripts/plan_sync.py CURRENT.txt SOURCE.md --preserve-prefix-blocks N --target-out TARGET.md > PLAN.json
```

`CURRENT.txt` may contain the full fetch response or only `<content>`. The script converts Markdown pipe tables to native Notion `<table header-row="true">` blocks, preserves fenced code including Mermaid, tokenizes top-level blocks, normalizes known rendering-only differences, computes an LCS, and emits exact unique `old_str`/`new_str` replacements.

6. Inspect `PLAN.json` and `TARGET.md`. Require every `replacement_checks` item to have `unique: true` and require `overlapping_replacements: false`. If not, apply only the first safe replacement, fetch again, and regenerate the plan; never use `replace_all_matches=true`.
7. Update the original page with `update_page(command="update_content")` and the emitted `content_updates`, which contain only tool parameters. Do not use `replace_content`. Update one page at a time and never write concurrently to the same page.
8. Fetch the page again and rerun the same command against the new fetch. Completion requires `semantic_equal: true`, `matched_blocks == current_blocks == target_blocks`, and zero replacements. Treat normalized discussion spans, generated `<colgroup>`, code-language aliases, and automatic links whose label equals their target as rendering differences only.

## Guardrails

- Preserve child pages, databases, folders, unknown blocks, synced blocks, and meeting-note transcripts unless the user explicitly requests their deletion or movement.
- If a discussion disappears after an update, stop and report its ID and former anchor.
- Stop if the source-to-page mapping, preserved prefix, or a replacement is ambiguous.
- Keep the pre-write discussion backup until the user accepts the verified page.
- Run the bundled check after changing diff, conversion, or normalization logic:

```bash
python3 <skill_dir>/scripts/plan_sync.py --self-check
```
