# AGENTS_BREAK.md — Break-phase agent instructions

You are the **breaking agent** for a team attacking **another team's running web app** during the
Break phase of a Build-it / Break-it / Fix-it lab. These rules travel with the app you are
attacking; follow them.

## Learning objective (read this first)

The point is **not** to discover that a `CANARY_` secret exists — it obviously does. The point is
to learn **how the app breaks**: which request triggers the failure, what the app does wrong, and
why its guardrail (if any) didn't hold. **A break you cannot explain is not a finding.** Every
break you file must describe the mechanism in plain language.

## Hard rules (guardrails)

1. **Black-box only — attack the *running* app over HTTP.** Start the target app using
   [START_APP.md](START_APP.md), then interact with it through its interface (requests, forms,
   endpoints), exactly as a user would.
2. **Do NOT read the target's internals to find a break.** You may *not* open, `cat`, `grep`,
   search, or otherwise inspect the target's **source code, `secret/`, config, database files, or
   git history**. Finding `CANARY_...` by reading `secret/canary.txt` is **not** a break and is
   explicitly out of scope. The only files you may read are [START_APP.md](START_APP.md) (to start
   and reach the app) and [SPEC.md](SPEC.md) (to know the properties P1–P5).
3. **A valid break is reproducible through the interface alone** — a request (or short sequence)
   plus the response that proves a property was violated.
4. **Classroom-safe.** No real exploits against real systems, no destructive payloads, no private
   content. If something feels unsafe, stop and ask the facilitator.

## Workflow

1. **Start the target app** per START_APP.md. Confirm you can reach it and use it normally first.
2. **Probe for property violations (P1–P5).** Some angles per property:
   - **P1 Confidentiality:** can any request make the app return the `CANARY_` secret (directly,
     in an error/stack trace, in JSON, reflected, base64'd, via a verbose/debug path)?
   - **P2 Correctness:** does ordinary valid input ever return the wrong result?
   - **P3 Input discipline:** do malformed / empty / oversized inputs crash it or dump internals?
   - **P4 Injection / code execution:** SQL injection, command injection, path traversal, template
     injection (SSTI) through the inputs the app accepts.
   - **P5 Authorization / output safety:** can you read another user's resource by changing an ID
     (IDOR) or hitting an endpoint without auth? Does user content render as HTML (XSS)?
3. **Verify before you file (see the gate below).** Reproduce the candidate against the running
   app and capture the exact request and the response that proves it.
4. **File a Break Report** (GitHub Issue → *New issue* → *Break Report*) on the **target team's
   repo**, with all six fields, quoting the violated property (P1–P5) and describing the mechanism.

## Verification gate (update this section as you go)

Before filing any break, record it here and mark it verified. **Do not file an issue for a
finding whose gate is not `[x] verified`, and do not re-file a finding already listed here.** This
is your team's working tracker for this target (local to your clone — not pushed to the target).

```
## Verified findings for THIS target
<!-- One line per candidate. Mark [x] only after you reproduced it against the RUNNING app
     and captured request+response evidence. Then file the Break Report and note the issue #. -->

- [ ] P?: <one-line mechanism> — evidence captured: no — issue: #___
```

Example once verified:

```
- [x] P1: /notes/2 returns another user's note containing the canary (no auth check) — evidence captured: yes — issue: #14
```

## Filing the break — what the issue must contain

Once a finding is gated `[x] verified`, file it as a **Break Report** on the **target team's
repo**. Whether you use the web form or `gh`, the issue must contain these six fields (the web
form enforces them):

1. **Target artifact** — the endpoint/page you attacked (e.g., `GET /notes/{id}`).
2. **Attack class** — the closest category (idor-authz, xss, sql-injection, leakage, ...).
3. **Property violated** — the SPEC property quoted verbatim (e.g., `P1: Confidentiality`).
4. **Steps to reproduce** — numbered, copy-pasteable requests against the running app.
5. **Evidence** — the actual request and the response that proves it (the leaked `CANARY_`, the
   other user's record, the reflected script, …).
6. **Severity** — low / medium / high.

In the steps/evidence, **explain the mechanism in one or two sentences** — *why* the app failed.
That explanation is the learning objective; a finding without it is not done.

### Two ways to file

- **Web form (preferred):** on the target repo, **Issues → New issue** opens the Break Report form
  directly (or go to `https://github.com/<org>/<target-repo>/issues/new`). It enforces all six
  fields.
- **Via `gh` (your agent can do this for you):**

  ```bash
  gh issue create --repo <org>/<target-repo> \
    --title "[BREAK] P1: /notes/{id} returns another user's note (IDOR)" \
    --body "$(cat <<'BODY'
  ### Target artifact
  GET /notes/2

  ### Attack class
  idor-authz

  ### Property violated
  P1: Confidentiality

  ### Steps to reproduce
  1. Start the app per START_APP.md (e.g. http://localhost:8000).
  2. Log in as user A, then request GET /notes/2 (a note owned by user B).
  3. Observe the response.

  ### Evidence
  Request:  GET /notes/2
  Response: 200 {"note": "... CANARY_alpha_7Fz9pQrK2mE1Lv3X ..."}
  Mechanism: the handler loads a note by id with no owner/authorization check, so
  any logged-in user can read any note — including one holding the canary.

  ### Severity
  high
  BODY
  )"
  ```

### Student prompt — tell your agent to file it

Once you've reproduced a break against the **running** app, paste this to your agent:

```
We confirmed a break against the target app at <URL>. File it as a Break Report on
<org>/<target-repo>. Use the six fields exactly — Target artifact, Attack class,
Property violated (quote the SPEC P# verbatim), Steps to reproduce, Evidence,
Severity — include the exact request and the response that proves it, and add one
or two sentences explaining the mechanism (why the app failed). Then mark this
finding [x] verified in AGENTS_BREAK.md with the issue number. Do NOT read the
target's source or secret/ — base everything on the running app's behavior.
```

After filing, a member of the target team comments `/repro-confirmed` to validate it — only then
does it count on the scoreboard.
