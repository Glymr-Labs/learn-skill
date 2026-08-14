# Learn Skill: Continuous Agent Learning

A framework-agnostic skill package for capturing what an AI agent learns during a session and persisting it as durable rules, reusable scripts, and architecture notes.

**Author:** Glymr — continuous learning for AI coding agents.

**Created by:** [Andrew Mata](https://github.com/andrewmata361)

**License:** [Apache License 2.0](LICENSE)

---

## Overview

The Learn Skill equips an agent to:

1. Capture preferences, conventions, architecture, and hard-won fixes from a conversation.
2. Filter candidates against a quality bar so only durable, actionable, recurring, non-obvious knowledge is kept.
3. **Propose** additions and removals, then write only what the user confirms.
4. Persist one-line rules to `AGENTS.md` or a harness-native global file. When a line is the wrong shape, add a project script or an architecture note instead.

Saving nothing is a valid outcome. Rules in `AGENTS.md` are injected into every future session, so noise is expensive.

---

## Install

Copy or symlink the whole `learn-skill/` folder (it must keep that name) into a skills path the harness discovers. The folder needs `SKILL.md`, `scripts/`, and `references/`.

| Harness | Personal (all projects) | Project (this repo) |
| :--- | :--- | :--- |
| Cursor | `~/.cursor/skills/learn-skill/` | `.cursor/skills/learn-skill/` |
| Codex | `~/.codex/skills/learn-skill/` | `.codex/skills/learn-skill/` |
| Claude Code | `~/.claude/skills/learn-skill/` | `.claude/skills/learn-skill/` |
| Cursor / multi-harness | `~/.agents/skills/learn-skill/` | `.agents/skills/learn-skill/` |

Cursor also loads skills from `.claude/skills/` and `.codex/skills/` for compatibility.

**Cursor personal install (Windows):**

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.cursor\skills" | Out-Null
Copy-Item -Recurse -Force "learn-skill" "$env:USERPROFILE\.cursor\skills\learn-skill"
```

Or symlink so edits in the repo apply everywhere:

```powershell
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.cursor\skills\learn-skill" -Target (Resolve-Path "learn-skill")
```

**Project install (shared with teammates):**

```powershell
New-Item -ItemType Directory -Force ".cursor\skills" | Out-Null
Copy-Item -Recurse -Force "learn-skill" ".cursor\skills\learn-skill"
```

After install, invoke with `/learn-skill`, or say `/learn` / "remember this".

To have wrap-up sessions trigger a learn pass automatically, add the snippet in [references/wrap-up-rule.md](references/wrap-up-rule.md). Do not bind this to a Cursor `stop` hook.

For Gemini CLI, NVIDIA/NeMo, or other custom harnesses, inject the system-prompt snippet in [references/integration_guide.md](references/integration_guide.md).

---

## Directory structure

```
learn-skill/
├── SKILL.md                          # Agent instructions
├── README.md
├── LICENSE
├── NOTICE
├── references/
│   ├── architecture.md               # Scopes, precedence, harness paths
│   ├── artifacts.md                  # Scripts and architecture notes
│   ├── extraction_prompt.txt         # Subagent / middleware prompt
│   ├── integration_guide.md          # Harness middleware
│   ├── pruning.md                    # Drop stale or time-boxed memory
│   └── wrap-up-rule.md               # Optional user rule
└── scripts/
    ├── memory_manager.py             # list / append / replace / remove
    └── test_memory_manager.py
```

---

## Where things go

| Artifact | Destination |
| :--- | :--- |
| Project rule | `AGENTS.md` at the git root, under `## Learned Rules` |
| Global rule | The file this IDE already loads (Cursor: `~/.cursor/rules/learned.mdc`) |
| Script | Project `scripts/`, plus a one-line rule that points at it |
| Architecture note | Existing `architecture.md` or `docs/architecture.md` |

Content outside `## Learned Rules` is never modified by the CLI.

---

## CLI usage

Run the script from this skill directory (or pass its absolute path). Agents must not call a project-local `scripts/memory_manager.py`.

```bash
python scripts/memory_manager.py --action list --scope project
python scripts/memory_manager.py --action append --scope project \
  --category "Security" --content "Always use parameterized SQL queries."
python scripts/memory_manager.py --action replace --scope project \
  --match "Old rule." --content "New rule."
python scripts/memory_manager.py --action remove --scope project \
  --match "Stale rule."
python scripts/memory_manager.py --action append --scope global \
  --category "Editor" --content "Prefer HSL over hex for CSS color values."
python scripts/memory_manager.py --action append --file path/to/rules.md \
  --content "Prefer composition over inheritance."
```

On Windows, if `python` is missing, use `py -3`.

Rules must be a single line. Exact duplicates, ignoring case, spacing, and a trailing period, are skipped.

Requires Python 3.8+ and no third-party packages.

```bash
python scripts/test_memory_manager.py
```

---

## Integration

See [references/integration_guide.md](references/integration_guide.md) for post-turn hook middleware and extraction-prompt wiring.
