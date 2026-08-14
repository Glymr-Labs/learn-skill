#!/usr/bin/env python3
"""
Memory manager CLI for the Learn Skill.

Reads, lists, appends, replaces, and removes single-line rules in persistent
agent memory files. Project scope targets AGENTS.md at the git/workspace root.
Global scope targets a harness-native rules file (or ~/.agents/rules.md).
Any other location can be addressed with --file.

Appended rules live under a '## Learned Rules' section, grouped into
'### <category>' subsections. Content outside that section is never modified.
"""

import argparse
import os
import re
import sys
from pathlib import Path

LEARNED_SECTION = "## Learned Rules"
DEFAULT_CATEGORY = "General"
HARNESSES = ("cursor", "claude", "codex", "gemini", "neutral")
MDC_FRONTMATTER = [
    "---",
    "description: Learned user preferences captured by the Learn skill",
    "alwaysApply: true",
    "---",
    "",
]


def _home(home=None):
    return Path(home).expanduser() if home else Path.home()


def global_path_for_harness(harness, home=None):
    """Return the native global memory path for a harness."""
    root = _home(home)
    paths = {
        "cursor": root / ".cursor" / "rules" / "learned.mdc",
        "claude": root / ".claude" / "CLAUDE.md",
        "codex": root / ".codex" / "AGENTS.md",
        "gemini": root / ".gemini" / "GEMINI.md",
        "neutral": root / ".agents" / "rules.md",
    }
    if harness not in paths:
        raise ValueError(
            "Unknown harness: {0}. Must be one of: {1}.".format(
                harness, ", ".join(HARNESSES)
            )
        )
    return paths[harness]


def detect_harness(home=None):
    """Pick a harness from LEARN_SKILL_HARNESS or which config dirs exist.

    If several harness dirs exist, Cursor wins, then Claude, Codex, Gemini.
    """
    env = os.environ.get("LEARN_SKILL_HARNESS", "").strip().lower()
    if env in HARNESSES:
        return env
    root = _home(home)
    for name, rel in (
        ("cursor", ".cursor"),
        ("claude", ".claude"),
        ("codex", ".codex"),
        ("gemini", ".gemini"),
    ):
        if (root / rel).exists():
            return name
    return "neutral"


def find_project_root(start):
    """Walk up from start until a .git directory is found; otherwise use start."""
    current = Path(start).expanduser().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return current


def get_target_path(
    scope,
    workspace_dir=None,
    custom_file=None,
    harness=None,
    home=None,
):
    """Resolve the target memory file path from an explicit path or a scope."""
    if custom_file:
        return Path(custom_file).expanduser()
    if scope == "global":
        chosen = harness or detect_harness(home=home)
        return global_path_for_harness(chosen, home=home)
    if scope == "project":
        start = Path(workspace_dir).expanduser() if workspace_dir else Path.cwd()
        return find_project_root(start) / "AGENTS.md"
    raise ValueError("Unknown scope: {0}. Must be 'global' or 'project'.".format(scope))


def read_memory(file_path):
    if not file_path.exists():
        return ""
    # utf-8-sig strips a BOM if present (common on Windows-created files).
    return file_path.read_text(encoding="utf-8-sig")


def normalize_rule(text):
    """Reduce a rule to a comparable form: no bullet marker, no case, no trailing period."""
    text = re.sub(r"^[-*+]\s+", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.lower().rstrip(".")


def is_duplicate(existing, rule):
    """True if an identical rule bullet is already present anywhere in the file."""
    target = normalize_rule(rule)
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "+ ")) and normalize_rule(stripped) == target:
            return True
    return False


def _heading_level(line):
    match = re.match(r"^(#{1,6})\s", line)
    return len(match.group(1)) if match else 0


def _section_bounds(lines, start, level):
    """Index one past the end of the section headed at `start`."""
    for i in range(start + 1, len(lines)):
        heading = _heading_level(lines[i])
        if 0 < heading <= level:
            return i
    return len(lines)


def _find_heading(lines, text, start=0, stop=None):
    stop = len(lines) if stop is None else stop
    for i in range(start, stop):
        if lines[i].strip().lower() == text.lower():
            return i
    return -1


def _insert_at_section_end(lines, start, end, block):
    """Insert `block` at the end of a section's content, before trailing blanks."""
    insert_at = end
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    return lines[:insert_at] + block + lines[insert_at:]


def _write_lines(file_path, lines):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_single_line(value, flag):
    if value is None:
        return None
    if "\n" in value or "\r" in value:
        raise ValueError(
            "{0} must be a single line; split multi-line input into "
            "separate rules and handle them one at a time".format(flag)
        )
    return " ".join(value.split())


def _find_bullet(lines, match):
    target = normalize_rule(match)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "+ ")) and normalize_rule(stripped) == target:
            return i
    return -1


def _learned_slice(lines):
    idx = _find_heading(lines, LEARNED_SECTION)
    if idx == -1:
        return -1, -1
    return idx, _section_bounds(lines, idx, 2)


def list_learned(file_path):
    existing = read_memory(file_path)
    if not existing.strip():
        return ""
    lines = existing.splitlines()
    start, end = _learned_slice(lines)
    if start == -1:
        return ""
    return "\n".join(lines[start:end]).strip()


def append_rule(file_path, content, category=DEFAULT_CATEGORY):
    """Insert a single-line rule under '## Learned Rules' -> '### <category>'.

    Returns True if the file was written, False if the rule was already present.
    """
    rule = _ensure_single_line(content, "--content")
    if not rule:
        raise ValueError("Rule content is empty.")

    existing = read_memory(file_path)
    if is_duplicate(existing, rule):
        print("[learn-skill] Already present in {0}, skipping: {1}".format(file_path, rule))
        return False

    bullet = "- {0}".format(rule)
    category_heading = "### {0}".format(category)
    lines = existing.splitlines()
    if not lines and file_path.suffix.lower() == ".mdc":
        lines = list(MDC_FRONTMATTER)

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

    _write_lines(file_path, lines)
    print("[learn-skill] Saved under '{0}' in {1}: {2}".format(category, file_path, rule))
    return True


def replace_rule(file_path, match, content):
    """Replace an existing rule bullet that matches `match` with `content`."""
    new_rule = _ensure_single_line(content, "--content")
    old_rule = _ensure_single_line(match, "--match")
    if not new_rule or not old_rule:
        raise ValueError("Both --match and --content are required for replace.")

    existing = read_memory(file_path)
    if not existing:
        raise ValueError("No memory file at {0}.".format(file_path))
    if is_duplicate(existing, new_rule) and normalize_rule(new_rule) != normalize_rule(old_rule):
        raise ValueError("Replacement already exists in {0}: {1}".format(file_path, new_rule))

    lines = existing.splitlines()
    idx = _find_bullet(lines, old_rule)
    if idx == -1:
        raise ValueError("No matching rule in {0}: {1}".format(file_path, old_rule))

    prefix = re.match(r"^(\s*[-*+]\s+)", lines[idx]).group(1)
    lines[idx] = "{0}{1}".format(prefix, new_rule)
    _write_lines(file_path, lines)
    print("[learn-skill] Replaced in {0}: {1} -> {2}".format(file_path, old_rule, new_rule))
    return True


def remove_rule(file_path, match):
    """Remove the first rule bullet that matches `match`."""
    old_rule = _ensure_single_line(match, "--match")
    if not old_rule:
        raise ValueError("--match is required for remove.")

    existing = read_memory(file_path)
    if not existing:
        raise ValueError("No memory file at {0}.".format(file_path))

    lines = existing.splitlines()
    idx = _find_bullet(lines, old_rule)
    if idx == -1:
        raise ValueError("No matching rule in {0}: {1}".format(file_path, old_rule))

    del lines[idx]
    _write_lines(file_path, lines)
    print("[learn-skill] Removed from {0}: {1}".format(file_path, old_rule))
    return True


def _configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main(argv=None):
    _configure_stdio()

    parser = argparse.ArgumentParser(description="Learn Skill memory manager")
    parser.add_argument(
        "--action",
        choices=["read", "list", "append", "replace", "remove"],
        required=True,
    )
    parser.add_argument("--scope", choices=["global", "project"], default="project")
    parser.add_argument("--file", type=str, default=None, help="Explicit target file path")
    parser.add_argument("--content", type=str, help="Single-line rule text")
    parser.add_argument("--match", type=str, help="Existing rule to replace or remove")
    parser.add_argument("--category", type=str, default=DEFAULT_CATEGORY)
    parser.add_argument("--workspace", type=str, default=None, help="Workspace root directory")
    parser.add_argument(
        "--harness",
        choices=list(HARNESSES),
        default=None,
        help="Native global path: cursor, claude, codex, gemini, or neutral",
    )

    args = parser.parse_args(argv)

    try:
        target_path = get_target_path(
            args.scope, args.workspace, args.file, harness=args.harness
        )
        if args.action == "read":
            content = read_memory(target_path)
            label = str(target_path) if args.file else "{0}: {1}".format(args.scope, target_path)
            print("=== Memory ({0}) ===".format(label))
            print(content if content.strip() else "(empty)")
            return
        if args.action == "list":
            learned = list_learned(target_path)
            label = str(target_path) if args.file else "{0}: {1}".format(args.scope, target_path)
            print("=== Learned Rules ({0}) ===".format(label))
            print(learned if learned else "(empty)")
            return
        if args.action == "append":
            if not args.content:
                parser.error("--content is required for append")
            append_rule(target_path, args.content, args.category)
            return
        if args.action == "replace":
            if not args.match or not args.content:
                parser.error("--match and --content are required for replace")
            replace_rule(target_path, args.match, args.content)
            return
        if args.action == "remove":
            target = args.match or args.content
            if not target:
                parser.error("--match (or --content) is required for remove")
            remove_rule(target_path, target)
            return
        raise ValueError("Unknown action: {0}".format(args.action))
    except Exception as exc:
        print("[learn-skill] Error: {0}".format(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
