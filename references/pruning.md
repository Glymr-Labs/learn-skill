# Pruning learned memory

Learned rules are cheap to add and expensive to leave. Every `/learn-skill` pass reviews existing bullets, not only new ones. There is no expiry date on a rule and no second slash command. Propose removals in the same table as additions.

---

## 1. When to drop a rule

Propose **Remove** if any of these are true:

- It would fail the quality bar if you saw it today (not durable, not actionable, obvious, or a secret).
- It is time-boxed or status: "focusing on X for a few days", "this week", "currently", "today we are…".
- This session contradicted it, or the user said it is no longer true / not needed.
- It duplicates or is fully covered by a stronger rule you are proposing.

If you are unsure, propose the removal as optional and say why. Do not silently delete.

---

## 2. How it shows up

Same proposal table as adds:

| Type | Scope | Destination | Change |
| :--- | :--- | :--- | :--- |
| Remove | project | AGENTS.md | User is focusing on networking for a few days. |

After confirm, run `--action remove --match` with the exact existing bullet text. For architecture notes, delete or rewrite the stale section in that file. For a script that is no longer used, delete the file only if the user confirms, and remove the rule that pointed at it.

---

## 3. What not to do

- Do not add `(expires: …)` or "until Friday" onto a rule. If it needs an expiry, it should not be a rule.
- Do not store current-focus or sprint status anywhere the agent loads every session.
- Do not prune hand-written text outside `## Learned Rules`.
- Do not run a background hook that deletes rules without a proposal.

---

## 4. Forget-only turns

If the user says "forget this", "unlearn", or "we don't need that" and points at a thing, skip the hunt for new rules unless they also asked to learn. List memory, propose the matching removals, wait, then remove.
