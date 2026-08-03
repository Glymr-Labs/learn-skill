#!/usr/bin/env python3
"""
Memory manager CLI for the Learn Skill.

Reads and appends single-line rules in persistent agent memory files. Project scope
targets AGENTS.md at the workspace root; global scope targets ~/.agents/rules.md.
Any other location can be addressed with --file.

Appended rules live under a '## Learned Rules' section, grouped into '### <category>'
subsections. Content outside that section is never modified.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_GLOBAL_PATH = Path.home() / ".agents" / "rules.md"
LEARNED_SECTION = "## Learned Rules"
DEFAULT_CATEGORY = "General"


def get_target_path(scope: str, workspace_dir: str = None, custom_file: str = None) -> Path:
    """Resolve the target memory file path from an explicit path or a scope."""
    if custom_file:
        return Path(custom_file).expanduser()
    if scope == "global":
        return DEFAULT_GLOBAL_PATH
    if scope == "project":
        base_dir = Path(workspace_dir).expanduser() if workspace_dir else Path.cwd()
        return base_dir / "AGENTS.md"
    raise ValueError(f"Unknown scope: {scope}. Must be 'global' or 'project'.")


def read_memory(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    # utf-8-sig strips a BOM if present (common on Windows-created files).
    return file_path.read_text(encoding="utf-8-sig")


def normalize_rule(text: str) -> str:
    """Reduce a rule to a comparable form: no bullet marker, no case, no trailing period."""
    text = re.sub(r"^[-*+]\s+", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.lower().rstrip(".")


def is_duplicate(existing: str, rule: str) -> bool:
    """True if an identical rule bullet is already present anywhere in the file."""
    target = normalize_rule(rule)
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "+ ")) and normalize_rule(stripped) == target:
            return True
    return False


def _heading_level(line: str) -> int:
    match = re.match(r"^(#{1,6})\s", line)
    return len(match.group(1)) if match else 0


def _section_bounds(lines: list, start: int, level: int) -> int:
    """Index one past the end of the section headed at `start`, i.e. the next heading
    at the same or a shallower level."""
    for i in range(start + 1, len(lines)):
        heading = _heading_level(lines[i])
        if 0 < heading <= level:
            return i
    return len(lines)


def _find_heading(lines: list, text: str, start: int = 0, stop: int = None) -> int:
    stop = len(lines) if stop is None else stop
    for i in range(start, stop):
        if lines[i].strip().lower() == text.lower():
            return i
    return -1


def _insert_at_section_end(lines: list, start: int, end: int, block: list) -> list:
    """Insert `block` at the end of a section's content, before its trailing blank lines."""
    insert_at = end
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    return lines[:insert_at] + block + lines[insert_at:]


def append_rule(file_path: Path, content: str, category: str = DEFAULT_CATEGORY) -> bool:
    """Insert a single-line rule under '## Learned Rules' -> '### <category>'.

    Returns True if the file was written, False if the rule was already present.
    """
    rule = " ".join(content.split())
    if not rule:
        raise ValueError("Rule content is empty.")

    existing = read_memory(file_path)
    if is_duplicate(existing, rule):
        print(f"[learn-skill] Already present in {file_path}, skipping: {rule}")
        return False

    bullet = f"- {rule}"
    category_heading = f"### {category}"
    lines = existing.splitlines()

    learned_idx = _find_heading(lines, LEARNED_SECTION)
    if learned_idx == -1:
        block = [LEARNED_SECTION, "", category_heading, bullet]
        if lines:
            while lines and not lines[-1].strip():
                lines.pop()
            lines.append("")
        lines.extend(block)
    else:
        learned_end = _section_bounds(lines, learned_idx, 2)
        category_idx = _find_heading(lines, category_heading, learned_idx + 1, learned_end)
        if category_idx == -1:
            lines = _insert_at_section_end(
                lines, learned_idx, learned_end, ["", category_heading, bullet]
            )
        else:
            category_end = _section_bounds(lines, category_idx, 3)
            lines = _insert_at_section_end(lines, category_idx, category_end, [bullet])

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[learn-skill] Saved under '{category}' in {file_path}: {rule}")
    return True


def main():
    # Avoid Windows console encode crashes when printing UTF-8 memory contents.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="Learn Skill memory manager")
    parser.add_argument("--action", choices=["read", "append"], required=True)
    parser.add_argument("--scope", choices=["global", "project"], default="project")
    parser.add_argument("--file", type=str, default=None, help="Explicit target file path")
    parser.add_argument("--content", type=str, help="Single-line rule to append")
    parser.add_argument("--category", type=str, default=DEFAULT_CATEGORY)
    parser.add_argument("--workspace", type=str, default=None, help="Workspace root directory")

    args = parser.parse_args()

    try:
        target_path = get_target_path(args.scope, args.workspace, args.file)
        if args.action == "read":
            content = read_memory(target_path)
            label = str(target_path) if args.file else f"{args.scope}: {target_path}"
            print(f"=== Memory ({label}) ===")
            print(content if content.strip() else "(empty)")
        else:
            if not args.content:
                parser.error("--content is required for append")
            if "\n" in args.content or "\r" in args.content:
                parser.error(
                    "--content must be a single line; split multi-line input into "
                    "separate rules and append them one at a time"
                )
            append_rule(target_path, args.content, args.category)
    except Exception as exc:
        print(f"[learn-skill] Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
