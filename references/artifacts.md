# Artifacts beyond one-line rules

Use this when a candidate is worth keeping but a single `AGENTS.md` bullet is the wrong shape. Rules stay the default. Scripts and architecture notes are for the cases a line cannot carry.

---

## 1. Decision order

1. **Rule** if one imperative sentence will change what an agent does next time.
2. **Script + rule** if the session produced a reusable command sequence that was actually run (or clearly will be). The script holds the steps; the rule points at it.
3. **Architecture note** if the knowledge is structural (how parts fit, invariants, data flow) and too large for one line. These files are read on demand, so they may be longer than a rule.
4. **Nothing** if it fails the quality bar in `SKILL.md`.

Never create a script or architecture file "in case it helps."

---

## 2. Scripts

Destination: the **project** `scripts/` directory (create it if needed). Do not add helpers to this skill package unless the change is to the Learn skill itself.

Write a script only when all of these hold:

- The sequence was executed in this session, or the user asked to keep it.
- Someone will run it again in this repo.
- The steps are non-obvious (flags, cwd, env, ordering).
- The file is runnable with the project's existing tools. No new dependencies unless the user agreed.

Style:

- One job per script. Name it after the job (`vendor_sync.py`, `reset_local_db.sh`).
- Put usage in a short top-of-file comment.
- No secrets. Read credentials from the environment.
- Prefer the language already used in `scripts/` or the repo's default.

After the user confirms the proposal, write the file, then append a one-line project rule:

```text
Refresh vendored dependencies with python scripts/vendor_sync.py.
```

That pairing is the useful form: cheap memory, real procedure.

---

## 3. Architecture notes

Destination, in order:

1. An existing `architecture.md` or `docs/architecture.md` (or a similarly named file the repo already uses).
2. If none exists and the note is truly structural, create `docs/architecture.md`.

Do not create `architecture.md` for a single sentence — that is a rule.

Each note is a short section, not a transcript:

```markdown
## Checkout pipeline

Orders enter through `api/checkout.py`. Workers pull from the `orders:pending` queue.
Do not charge a card by calling the worker handler from the HTTP handler.
```

Rules for the file:

- Facts and invariants only. No "today we decided" narration.
- Update or replace a stale section rather than appending a second copy.
- Keep it skimmable. Link to code paths instead of pasting them.
- If a one-line constraint falls out of the note, also add that line as a rule.

---

## 4. What still does not belong

- New Cursor/Claude skills generated from a session. That is a different workflow.
- Speculative helpers the user never ran.
- Session recaps, ticket status, or design essays.
- Duplicating something already obvious from the repo tree or README.
