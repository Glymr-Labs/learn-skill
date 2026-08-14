# Wrap-up user rule

Cursor will not run this skill at session end on its own. Add the following to a
user rule (`~/.cursor/rules`) or the project `AGENTS.md` if you want wrap-up to
trigger a learn pass. Do not attach this to a `stop` / `sessionEnd` hook — that
fires every agent turn and would flood memory.

```text
When the user is wrapping up, says they are done, or asks to close out a session,
run /learn-skill. Propose durable rules (and any reusable scripts or
architecture notes) and propose removals for time-boxed or stale learned
rules. Wait for confirmation before writing. Saving nothing is a valid outcome.
```

The skill can also be invoked directly with `/learn-skill`.
