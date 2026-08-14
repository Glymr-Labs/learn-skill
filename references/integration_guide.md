# Integration Guide

How to wire the Learn Skill into a custom agent harness, multi-agent framework, or CLI runner.

---

## 1. Two integration patterns

**Agent-driven (default).** The main agent reads `SKILL.md` when a trigger fires, proposes artifacts, waits for confirmation, then calls `memory_manager.py` or edits files. Nothing to build; drop the skill directory where the harness discovers skills. Install the folder as `learn-skill` so `/learn-skill` works.

**Post-turn hook.** The harness fires a background distillation pass on a defined event: a `/learn-skill` command, session close, or explicit user feedback. This path writes without a UI confirm, so keep it behind an explicit trigger. Do not bind it to Cursor `stop` / `sessionEnd` — those fire every agent turn.

---

## 2. Harness middleware

The extraction step is a model call, not string manipulation. Raw transcript text must never reach the memory file.

```python
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

EXTRACTION_PROMPT = (Path(__file__).parent / "extraction_prompt.txt").read_text(
    encoding="utf-8"
)

TRIGGERS = ("/learn", "/learn-skill", "remember this", "save this rule", "learn this pattern")


class LearnSkillMiddleware:
    """Distills a transcript into rules and persists them via memory_manager.py."""

    def __init__(
        self,
        skill_dir: str,
        llm: Callable[[str], str],
        workspace: str = ".",
        harness: str = "cursor",
    ):
        self.script = Path(skill_dir) / "scripts" / "memory_manager.py"
        self.llm = llm
        self.workspace = workspace
        self.harness = harness

    def should_trigger(self, user_message: str) -> bool:
        lowered = user_message.lower()
        return any(trigger in lowered for trigger in TRIGGERS)

    def extract(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Ask the model for items. Returns [] when nothing clears the quality bar."""
        transcript_text = "\n".join(f"{m['role']}: {m['content']}" for m in transcript)
        existing = self._read_memory()
        prompt = EXTRACTION_PROMPT.replace("{{TRANSCRIPT_TEXT}}", transcript_text).replace(
            "{{EXISTING_MEMORY_TEXT}}", existing
        )

        response = self.llm(prompt).strip()
        if response == "NONE":
            return []

        items = []
        for line in response.splitlines():
            parts = [part.strip() for part in line.split("|", 3)]
            if len(parts) != 4:
                continue
            kind, scope, category, text = parts
            kind = kind.upper()
            scope = scope.upper()
            if kind not in {"RULE", "SCRIPT", "ARCH"} or scope not in {"GLOBAL", "PROJECT"}:
                continue
            if not text:
                continue
            items.append(
                {"kind": kind, "scope": scope, "category": category, "text": text}
            )
        return items

    def persist_rules(self, items: List[Dict[str, str]]) -> List[str]:
        """Write RULE items only. Scripts and architecture notes are agent-edited files."""
        results = []
        for entry in items:
            if entry["kind"] != "RULE":
                continue
            scope = "global" if entry["scope"] == "GLOBAL" else "project"
            cmd = [
                sys.executable,
                str(self.script),
                "--action",
                "append",
                "--scope",
                scope,
                "--workspace",
                self.workspace,
                "--category",
                entry["category"],
                "--content",
                entry["text"],
            ]
            if scope == "global":
                cmd.extend(["--harness", self.harness])
            result = subprocess.run(cmd, capture_output=True, text=True)
            results.append(result.stdout.strip() or result.stderr.strip())
        return results

    def run(self, transcript: List[Dict[str, Any]]) -> List[str]:
        return self.persist_rules(self.extract(transcript))

    def _read_memory(self) -> str:
        chunks = []
        for scope, extra in (
            ("project", []),
            ("global", ["--harness", self.harness]),
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--action",
                    "list",
                    "--scope",
                    scope,
                    "--workspace",
                    self.workspace,
                    *extra,
                ],
                capture_output=True,
                text=True,
            )
            chunks.append(result.stdout)
        return "\n".join(chunks)
```

Keep `extraction_prompt.txt` next to this guide (same `references/` folder) so it does not drift from a second handwritten copy.

Report every saved item back to the user. Silent memory writes are hard to trust.

---

## 3. System prompt injection

For harnesses that do not auto-discover skills, add:

```text
## LEARNING & MEMORY
When the user says "/learn-skill" or "/learn", corrects you, or establishes a new standard, read
learn-skill/SKILL.md and follow it. Propose durable rules,
and any reusable scripts or architecture notes, then wait for confirmation
before writing. Save a rule only if it is durable, actionable, recurring, and
non-obvious. Never persist secrets, personal identifiers, or transcript text.
Report what you saved and where. Saving nothing is a valid outcome.
```

---

## 4. Verification

```bash
python scripts/test_memory_manager.py
```

Or by hand, pointing `--file` at a scratch path:

```bash
TMP=$(mktemp -d)/AGENTS.md

python scripts/memory_manager.py --action append --file "$TMP" \
  --category "Build & Test" --content "Run linting before committing."

python scripts/memory_manager.py --action append --file "$TMP" \
  --category "Build & Test" --content "Run linting before committing."

python scripts/memory_manager.py --action list --file "$TMP"
```

Expected: a `## Learned Rules` section containing one `### Build & Test` subsection with a single bullet.
