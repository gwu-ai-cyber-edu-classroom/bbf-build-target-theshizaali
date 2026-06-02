# BBF Day - Flask URL Shortener

Chosen build-menu target: **15 - URL shortener service**  
Platform: **Flask**  
Canary surface: **a private/admin link**

This app creates local short links at `/u/<code>`. Public links can be created from the home page or JSON API. A seeded private admin link is created on first run with a random, non-sequential code and is only visible or usable after admin sign-in.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The app uses file storage at `data/links.json`. Delete that file to reset the seeded links.

## Admin Access

By default, the admin password is the `CANARY_` value already present under `secret/`. The app reads it for authentication but does not render it in HTML, JSON, redirects, logs, or error pages.

For a demo password that is not the canary, run:

```bash
SHORTY_ADMIN_PASSWORD='choose-a-demo-password' python app.py
```

## Redirect Policy

To avoid becoming an open redirector, new destinations must be absolute HTTPS URLs on the allowed host list. The default hosts are:

- `docs.python.org`
- `flask.palletsprojects.com`
- `www.openai.com`
- `example.com`
- subdomains of `example.com`

Override them with a comma-separated list:

```bash
SHORTY_ALLOWED_HOSTS='docs.python.org,example.edu,.example.edu' python app.py
```

## API

Create a public short link:

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d '{"title":"Python Docs","target_url":"https://docs.python.org/3/"}' \
  http://127.0.0.1:5000/api/links
```

List public links:

```bash
curl -s http://127.0.0.1:5000/api/links
```

Private links are omitted from the public API and return the same 404 as a missing code when requested without an admin session.

## Security Notes

- **P1 Confidentiality:** the app reads the canary for admin authentication and keeps only a `secret_ref` marker in the seeded private link record. It never returns the canary value.
- **P2 Correctness:** valid public links are shortened and redirect to their stored destination.
- **P3 Input discipline:** empty, malformed, oversized, non-HTTPS, credentialed, or off-list URLs are rejected without stack traces.
- **P4 No injection/code execution:** user input is stored as data only; it is not executed as code, shell, SQL, paths, or templates.
- **P5 Authorization/output safety:** private links require an admin session, public enumeration excludes private records, and rendered user text is escaped by Jinja.

## Checks

```bash
pytest tests/build_check.py
pytest tests/test_shortener.py
```

`tests/test_shortener.py` requires Flask, so install `requirements.txt` first.
