# START_APP.md — how to run and probe this app

> **Build team:** fill in every `<...>` below once your app runs. Other teams use this file to
> start your app and probe it during Break. Keep it accurate — a break is filed against the app a
> breaker can actually start from these instructions.

## What this app is

- **App:** <one line — e.g., "a paste-bin service" (menu #1)>
- **Stack:** <Python + Flask / FastAPI, or Node + Express>

## Start it

```bash
# 1. Install dependencies
<e.g. pip install -r requirements.txt   OR   npm install>

# 2. Run it
<e.g. flask --app app run --port 8000   OR   uvicorn app:app --port 8000   OR   node server.js>
```

- **Base URL:** <e.g. http://localhost:8000>
- **Stop it:** Ctrl-C in the terminal running it.

## How to interact with it

- **Main endpoints / pages:**
  - `<METHOD> <path>` — <what it does> — <example>
  - `<METHOD> <path>` — <what it does> — <example>
- **Accounts / credentials for legitimate use** (if the app has login): <demo username/password, or "none">
- **A benign request that should succeed:**

  ```bash
  <e.g. curl http://localhost:8000/notes/1>
  ```

## For breakers

Attack this **running app over HTTP** — do **not** read this repo's source or `secret/` to find a
break. See [AGENTS_BREAK.md](AGENTS_BREAK.md) for the rules and your AI agent's instructions, and
[SPEC.md](SPEC.md) for the five properties (P1–P5) you are probing for.
