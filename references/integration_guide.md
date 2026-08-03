# Integration Guide

How to wire the Learn Skill into a custom agent harness, multi-agent framework, or CLI runner.

---

## 1. Two integration patterns

**Agent-driven.** The main agent reads `SKILL.md` when a trigger fires and performs the extraction itself, calling `memory_manager.py` or editing the memory file directly. Nothing to build; drop the skill directory where the harness discovers skills.

**Post-turn hook.** The harness fires a background distillation pass on a defined event: a `/learn` command, session close, an error-recovery completion, or explicit user feedback. This requires the wiring below.

---

## 2. Harness middleware

The extraction step is a model call, not string manipulation. Raw transcript text must never reach the memory file: the model's job is to distill rules, and the quality bar is what keeps memory from filling with noise.

```python
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List

EXTRACTION_PROMPT = (Path(__file__).parent / "extraction_prompt.txt").read_text()

TRIGGERS = ("/learn", "remember this", "save this rule", "learn this pattern")


class LearnSkillMiddleware:
    """Distills a transcript into rules and persists them via memory_manager.py."""

    def __init__(self, skill_dir: str, llm: Callable[[str], str], workspace: str = "."):
        self.script = Path(skill_dir) / "scripts" / "memory_manager.py"
        self.llm = llm  # any callable taking a prompt and returning completion text
        self.workspace = workspace

    def should_trigger(self, user_message: str) -> bool:
        lowered = user_message.lower()
        return any(trigger in lowered for trigger in TRIGGERS)

    def extract(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Ask the model for rules. Returns [] when nothing clears the quality bar."""
        transcript_text = "\n".join(f"{m['role']}: {m['content']}" for m in transcript)
        existing = self._read_memory()
        prompt = EXTRACTION_PROMPT.replace("{{TRANSCRIPT_TEXT}}", transcript_text).replace(
            "{{EXISTING_MEMORY_TEXT}}", existing
        )

        response = self.llm(prompt).strip()
        if response == "NONE":
            return []

        rules = []
        for line in response.splitlines():
            parts = [part.strip() for part in line.split("|", 2)]
            if len(parts) != 3:
                continue  # ignore malformed lines rather than writing garbage
            scope, category, rule = parts
            if scope.upper() not in {"GLOBAL", "PROJECT"} or not rule:
                continue
            rules.append({"scope": scope.upper(), "category": category, "rule": rule})
        return rules

    def persist(self, rules: List[Dict[str, str]]) -> List[str]:
        """Write each rule and return the script's output lines for reporting."""
        results = []
        for entry in rules:
            scope = "global" if entry["scope"] == "GLOBAL" else "project"
            result = subprocess.run(
                [
                    "python", str(self.script),
                    "--action", "append",
                    "--scope", scope,
                    "--workspace", self.workspace,
                    "--category", entry["category"],
                    "--content", entry["rule"],
                ],
                capture_output=True,
                text=True,
            )
            results.append(result.stdout.strip() or result.stderr.strip())
        return results

    def run(self, transcript: List[Dict[str, Any]]) -> List[str]:
        return self.persist(self.extract(transcript))

    def _read_memory(self) -> str:
        result = subprocess.run(
            ["python", str(self.script), "--action", "read",
             "--scope", "project", "--workspace", self.workspace],
            capture_output=True,
            text=True,
        )
        return result.stdout
```

Copy the extraction prompt from section 6 of [SKILL.md](../SKILL.md) into `extraction_prompt.txt`, or inline it. Keeping one copy avoids the two drifting apart.

Report every saved rule back to the user. Silent memory writes are hard to trust and harder to debug.

---

## 3. System prompt injection

For harnesses that do not auto-discover skills, add:

```text
## LEARNING & MEMORY
When the user says "/learn", corrects you, or establishes a new standard, read
learn-skill/SKILL.md and follow it. Save a rule only if it is durable, actionable,
recurring, and non-obvious. Never persist secrets, personal identifiers, or
transcript text. Report what you saved and where. Saving nothing is a valid outcome.
```

---

## 4. Verification

Check the setup without touching real memory by pointing `--file` at a scratch path:

```bash
TMP=$(mktemp -d)/AGENTS.md

python scripts/memory_manager.py --action append --file "$TMP" \
  --category "Build & Test" --content "Run linting before committing."

# Repeating the same rule should report a skip, not a second bullet.
python scripts/memory_manager.py --action append --file "$TMP" \
  --category "Build & Test" --content "Run linting before committing."

python scripts/memory_manager.py --action read --file "$TMP"
```

Expected: a `## Learned Rules` section containing one `### Build & Test` subsection with a single bullet.

To inspect real project memory without modifying it:

```bash
python scripts/memory_manager.py --action read --scope project
```
