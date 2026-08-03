# Learn Skill: Continuous Agent Learning

A framework-agnostic skill package for capturing what an AI agent learns during a session and persisting it as durable rules.

**Author:** Glymr — continuous learning for AI coding agents.

**License:** [Apache License 2.0](LICENSE)

---


## Overview

The Learn Skill equips an agent to:

1. Capture preferences, code conventions, architecture standards, and hard-won fixes from a conversation.
2. Filter candidates against a quality bar so only durable, actionable, recurring, non-obvious knowledge is kept.
3. Append deduplicated one-line rules to `AGENTS.md` (project scope) or a configurable global memory file.

Saving nothing is a valid outcome. Memory is injected into every future session, so noise is expensive.

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

After install, invoke with `/learn-skill`, or say `/learn` / "remember this" so the agent loads it at session end.

For Gemini CLI, NVIDIA/NeMo, or other custom harnesses with no skills folder, inject the system-prompt snippet in [references/integration_guide.md](references/integration_guide.md) and point memory at `AGENTS.md` or a native rules path via `--file`.

---

## Directory structure

```
learn-skill/
├── SKILL.md                          # Agent instructions: triggers, quality bar, rule format, workflow
├── README.md                         # This document
├── references/
│   ├── architecture.md               # Scopes, precedence, per-harness memory locations
│   └── integration_guide.md          # Harness middleware and verification
└── scripts/
    └── memory_manager.py             # CLI for reading and appending rules
```

---

## Where rules go

| Scope | Destination |
| :--- | :--- |
| Project | `AGENTS.md` at repo root, under a `## Learned Rules` section |
| Global | `~/.agents/rules.md` by default, or any path via `--file` |

`AGENTS.md` is the project default because Cursor, Codex, Gemini CLI, and other harnesses read it automatically. Content outside the `## Learned Rules` section is never modified. See [references/architecture.md](references/architecture.md) for native global-memory locations per harness.

---

## CLI usage

Run these from the skill directory (the repo root after cloning this project). If the package is nested inside another repo, prefix paths with `learn-skill/`.

Append a rule:

```bash
python scripts/memory_manager.py --action append --scope project \
  --category "Security" --content "Always use parameterized SQL queries."
```

Read current memory:

```bash
python scripts/memory_manager.py --action read --scope project
```

Target an arbitrary file:

```bash
python scripts/memory_manager.py --action append --file path/to/rules.md \
  --content "Prefer composition over inheritance."
```

Rules must be a single line. Exact duplicates, ignoring case, spacing, and a trailing period, are skipped. Rewriting or removing an existing rule is done by editing the file directly.

Requires Python 3.8+ and no third-party packages.

---

## Integration

See [references/integration_guide.md](references/integration_guide.md) for post-turn hook middleware, the extraction prompt wiring, and a verification script that writes to a scratch file.
