# AGENTS.md — how your AI agent must operate in this repo

This is a **Build-it / Break-it / Fix-it** lab. The same repo is used in three very different
phases, and your agent must behave differently in each. **Read the gate below before doing
anything else.**

---

## ⛔ Phase gate — do this first, every session

Before writing code, reading files broadly, or taking any action, **establish the current phase**:

1. Read the **`PHASE`** file at the repo root. Its first line is one of: `build`, `break`, `fix`.
2. If `PHASE` is missing or you are unsure, **ask the user**: *"Are we in BUILD, BREAK, or FIX?"*
   and write their answer to `PHASE`.
3. **If this repo belongs to another team and you are attacking it, the phase is `break`** — set
   `PHASE` to `break` and follow the Break section only. Never operate in `build`/`fix` mode on a
   repo that is not your team's.

Then follow **only** the matching section below. If asked to do something outside the current
phase, stop and confirm the phase with the user.

Shared rules in every phase: stay **classroom-safe** (no real exploits against real systems, no
destructive actions, no private content), and treat [SPEC.md](SPEC.md) as the definition of the
five properties (P1–P5).

---

## 🔨 BUILD mode (`PHASE = build`) — your team's app

Goal: ship a small **working web app** from [BUILD-MENU.md](BUILD-MENU.md) that satisfies
[SPEC.md](SPEC.md), within the Build time box.

- Build the simplest working version first (a real HTTP app on `localhost`); harden later.
- Put the `CANARY_` secret from `secret/` into the app's data (e.g., a private record) so the app
  *uses* it but is expected never to leak it.
- **Leave the security decisions to the team.** Do not silently add hardening, sanitizing, auth,
  or output escaping, and do not scan for or warn about vulnerabilities unless the team asks — the
  Break and Fix phases are where that learning happens.
- When the app runs, **fill in [START_APP.md](START_APP.md)** with the exact start command, base
  URL, and endpoints so other teams can run and probe it.
- Keep `tests/build_check.py` green (a spec and a canary must be present).

## 💥 BREAK mode (`PHASE = break`) — another team's app

**Defer to [AGENTS_BREAK.md](AGENTS_BREAK.md). Follow it exactly.** In short:

- Attack the **running app over HTTP** (start it via the target's `START_APP.md`).
- **Do NOT read the target's source, `secret/`, config, database, or git history** to find a
  break. Finding the canary by reading files is out of scope. The learning objective is to
  understand **how** the app breaks through its interface.
- **Verify** each candidate against the running app, record it in the AGENTS_BREAK.md verification
  gate, and only then **file a Break Report** (GitHub Issue) on the target repo with all six
  fields, quoting the violated property.

## 🛠️ FIX mode (`PHASE = fix`) — your team's app, after breaks land

Goal: close confirmed breaks filed against your repo without regressing the build.

- Read the valid issues: `gh issue list --label valid` (or view Issues on your repo).
- **Triage in `fix_notes.md` before writing code:** pick the 1–2 breaks you'll fix and why. This
  triage is itself graded — an honest "we'd fix X next, here's why" is full credit.
- One **PR per fix**, body includes `closes #N` so the issue auto-closes on merge. The PR template
  asks which layer the fix lands at.
- After each fix, **re-verify** that the issue's reproduction no longer reproduces against the
  running app, and that `tests/build_check.py` still passes.
- Do **not** introduce new breaks while fixing.
