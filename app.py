"""Local Flask URL shortener for the BBF workshop target.

Run with:
    python app.py
"""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    get_flashed_messages,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_STORAGE = DATA_DIR / "links.json"
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{3,31}$")
CANARY_RE = re.compile(r"CANARY_[^\s\"'<>]+")
MAX_TITLE_LENGTH = 80
MAX_URL_LENGTH = 2048
DEFAULT_ALLOWED_HOSTS = {
    "docs.python.org",
    "flask.palletsprojects.com",
    "www.openai.com",
    "example.com",
    ".example.com",
}


INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1d242f;
      --muted: #5d6675;
      --line: #d8dde6;
      --paper: #f6f7f9;
      --panel: #ffffff;
      --accent: #0d766e;
      --accent-ink: #ffffff;
      --warn: #9f3412;
      --ok-bg: #e9f8f1;
      --bad-bg: #fff1eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1100px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 68px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1, h2 {
      margin: 0;
      letter-spacing: 0;
    }
    h1 {
      font-size: 24px;
      font-weight: 720;
    }
    h2 {
      font-size: 17px;
      font-weight: 700;
    }
    main {
      padding: 26px 0 44px;
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr;
      gap: 18px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    form {
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }
    input[type="text"],
    input[type="password"],
    input[type="url"] {
      width: 100%;
      min-height: 40px;
      border: 1px solid #c7ccd6;
      border-radius: 6px;
      padding: 9px 11px;
      color: var(--ink);
      font: inherit;
      background: #ffffff;
    }
    input:focus {
      outline: 3px solid rgba(13, 118, 110, 0.2);
      border-color: var(--accent);
    }
    .row {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .check {
      display: flex;
      grid-template-columns: auto 1fr;
      gap: 8px;
      align-items: center;
      color: var(--ink);
      font-weight: 600;
    }
    button,
    .button {
      appearance: none;
      min-height: 40px;
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 8px 13px;
      background: var(--accent);
      color: var(--accent-ink);
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
    }
    .button.secondary,
    button.secondary {
      background: #ffffff;
      color: var(--ink);
      border-color: #c7ccd6;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      table-layout: fixed;
    }
    th,
    td {
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .tag {
      display: inline-flex;
      min-height: 24px;
      align-items: center;
      border-radius: 999px;
      padding: 2px 8px;
      background: #edf2f7;
      color: #354052;
      font-size: 12px;
      font-weight: 700;
    }
    .tag.private {
      background: #fef0d8;
      color: #7c3d07;
    }
    .muted {
      color: var(--muted);
    }
    .flash {
      margin: 0 0 14px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
    }
    .flash.error {
      border-color: #fecab3;
      background: var(--bad-bg);
      color: var(--warn);
    }
    .flash.success {
      border-color: #b7e6ce;
      background: var(--ok-bg);
      color: #16633d;
    }
    .empty {
      margin: 14px 0 0;
      color: var(--muted);
    }
    @media (max-width: 760px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 16px 0;
      }
      .grid {
        grid-template-columns: 1fr;
      }
      table {
        font-size: 14px;
      }
      th:nth-child(3),
      td:nth-child(3) {
        display: none;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>Shortlink Desk</h1>
      <nav class="row" aria-label="Account">
        {% if admin %}
          <a class="button secondary" href="{{ url_for('admin') }}">Admin</a>
          <form method="post" action="{{ url_for('logout') }}" style="display:inline; margin:0;">
            <input type="hidden" name="csrf" value="{{ csrf_token() }}">
            <button class="secondary" type="submit">Sign out</button>
          </form>
        {% else %}
          <a class="button secondary" href="{{ url_for('login') }}">Admin</a>
        {% endif %}
      </nav>
    </div>
  </header>
  <main class="wrap">
    {% for category, message in messages %}
      <div class="flash {{ category }}">{{ message }}</div>
    {% endfor %}
    {{ body|safe }}
  </main>
</body>
</html>
"""


HOME_BODY = """
<div class="grid">
  <section class="panel" aria-labelledby="create-heading">
    <h2 id="create-heading">Create Link</h2>
    <form method="post" action="{{ url_for('create_link') }}">
      <input type="hidden" name="csrf" value="{{ csrf_token() }}">
      <label>
        Title
        <input name="title" type="text" maxlength="{{ max_title_length }}" required>
      </label>
      <label>
        Destination URL
        <input name="target_url" type="url" maxlength="{{ max_url_length }}" required>
      </label>
      <label>
        Custom code
        <input name="alias" type="text" maxlength="32" pattern="[A-Za-z0-9][A-Za-z0-9_-]{3,31}">
      </label>
      {% if admin %}
        <label class="check">
          <input name="private" type="checkbox" value="1">
          Private
        </label>
      {% endif %}
      <button type="submit">Create</button>
    </form>
  </section>
  <section class="panel" aria-labelledby="public-heading">
    <h2 id="public-heading">Public Links</h2>
    {% if links %}
      <table>
        <thead>
          <tr>
            <th style="width:32%;">Title</th>
            <th style="width:30%;">Short URL</th>
            <th>Host</th>
            <th style="width:80px;">Hits</th>
          </tr>
        </thead>
        <tbody>
          {% for link in links %}
            <tr>
              <td>{{ link.title }}</td>
              <td><a href="{{ url_for('follow_link', code=link.code) }}">{{ request.host_url.rstrip('/') }}{{ url_for('follow_link', code=link.code) }}</a></td>
              <td class="muted">{{ host_for(link.target_url) }}</td>
              <td>{{ link.hits }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="empty">No public links yet.</p>
    {% endif %}
  </section>
</div>
"""


LOGIN_BODY = """
<section class="panel" style="max-width: 420px;" aria-labelledby="login-heading">
  <h2 id="login-heading">Admin Sign In</h2>
  <form method="post" action="{{ url_for('login') }}">
    <input type="hidden" name="csrf" value="{{ csrf_token() }}">
    <label>
      Password
      <input name="password" type="password" autocomplete="current-password" required>
    </label>
    <button type="submit">Sign in</button>
  </form>
</section>
"""


ADMIN_BODY = """
<section class="panel" aria-labelledby="admin-heading">
  <div class="row" style="justify-content: space-between;">
    <h2 id="admin-heading">Admin Links</h2>
    <a class="button secondary" href="{{ url_for('home') }}">Back</a>
  </div>
  <table>
    <thead>
      <tr>
        <th style="width:24%;">Title</th>
        <th style="width:24%;">Short URL</th>
        <th>Host</th>
        <th style="width:90px;">Access</th>
        <th style="width:80px;">Hits</th>
      </tr>
    </thead>
    <tbody>
      {% for link in links %}
        <tr>
          <td>{{ link.title }}</td>
          <td><a href="{{ url_for('follow_link', code=link.code) }}">{{ request.host_url.rstrip('/') }}{{ url_for('follow_link', code=link.code) }}</a></td>
          <td class="muted">{{ host_for(link.target_url) }}</td>
          <td>
            {% if link.private %}
              <span class="tag private">Private</span>
            {% else %}
              <span class="tag">Public</span>
            {% endif %}
          </td>
          <td>{{ link.hits }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
"""


ERROR_BODY = """
<section class="panel" style="max-width: 560px;" aria-labelledby="error-heading">
  <h2 id="error-heading">{{ heading }}</h2>
  <p class="empty">{{ detail }}</p>
  <p><a class="button secondary" href="{{ url_for('home') }}">Back</a></p>
</section>
"""


def create_app(storage_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SHORTY_SESSION_SECRET", secrets.token_hex(32)),
        STORAGE_PATH=Path(storage_path or os.getenv("SHORTY_STORAGE", DEFAULT_STORAGE)),
        MAX_CONTENT_LENGTH=16 * 1024,
    )

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["host_for"] = host_for

    @app.before_request
    def prepare_storage():
        ensure_storage(app.config["STORAGE_PATH"])

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def home():
        links = public_links(load_links())
        body = render_template_string(
            HOME_BODY,
            links=links,
            admin=is_admin(),
            max_title_length=MAX_TITLE_LENGTH,
            max_url_length=MAX_URL_LENGTH,
        )
        return render_page("Shortlink Desk", body)

    @app.post("/links")
    def create_link():
        require_csrf()
        try:
            link = make_link(
                title=request.form.get("title", ""),
                target_url=request.form.get("target_url", ""),
                alias=request.form.get("alias", ""),
                private=bool(request.form.get("private")) and is_admin(),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("home"))

        links = load_links()
        if link["code"] in links:
            flash("That short code is already in use.", "error")
            return redirect(url_for("home"))
        links[link["code"]] = link
        save_links(links)
        flash("Short link created.", "success")
        return redirect(url_for("home"))

    @app.get("/u/<code>")
    def follow_link(code: str):
        if not CODE_RE.fullmatch(code):
            abort(404)

        links = load_links()
        link = links.get(code)
        if not link:
            abort(404)
        if link.get("private") and not is_admin():
            abort(404)

        try:
            target_url = normalize_target(str(link.get("target_url", "")))
        except ValueError:
            abort(404)

        link["hits"] = int(link.get("hits", 0)) + 1
        links[code] = link
        save_links(links)
        return redirect(target_url, code=302)

    @app.get("/login")
    def login_form():
        if is_admin():
            return redirect(url_for("admin"))
        body = render_template_string(LOGIN_BODY)
        return render_page("Admin Sign In", body)

    @app.post("/login")
    def login():
        require_csrf()
        expected = admin_password()
        submitted = request.form.get("password", "")
        if expected and hmac.compare_digest(submitted, expected):
            session["admin"] = True
            session.pop("csrf", None)
            return redirect(url_for("admin"))
        flash("Invalid credentials.", "error")
        return redirect(url_for("login_form"))

    @app.post("/logout")
    def logout():
        require_csrf()
        session.clear()
        flash("Signed out.", "success")
        return redirect(url_for("home"))

    @app.get("/admin")
    def admin():
        require_admin()
        links = all_links(load_links())
        body = render_template_string(ADMIN_BODY, links=links)
        return render_page("Admin Links", body)

    @app.get("/api/links")
    def api_links():
        links = [public_link_payload(link) for link in public_links(load_links())]
        return jsonify({"links": links})

    @app.post("/api/links")
    def api_create_link():
        payload = request.get_json(silent=True) or {}
        private = bool(payload.get("private"))
        if private and not is_admin():
            return jsonify({"error": "Admin access required."}), 403
        try:
            link = make_link(
                title=str(payload.get("title", "")),
                target_url=str(payload.get("target_url", "")),
                alias=str(payload.get("alias", "")),
                private=private,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        links = load_links()
        if link["code"] in links:
            return jsonify({"error": "That short code is already in use."}), 409
        links[link["code"]] = link
        save_links(links)
        return jsonify(public_link_payload(link)), 201

    @app.get("/api/admin/links")
    def api_admin_links():
        require_admin()
        links = [admin_link_payload(link) for link in all_links(load_links())]
        return jsonify({"links": links})

    @app.errorhandler(400)
    def bad_request(_error):
        return render_error("Bad Request", "The request could not be processed."), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_error("Forbidden", "Admin access is required."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_error("Not Found", "No matching short link was found."), 404

    return app


def render_page(title: str, body: str):
    return render_template_string(
        INDEX_TEMPLATE,
        title=title,
        body=body,
        admin=is_admin(),
        messages=get_flashed_messages(with_categories=True),
    )


def render_error(heading: str, detail: str):
    body = render_template_string(ERROR_BODY, heading=heading, detail=detail)
    return render_page(heading, body)


def is_admin() -> bool:
    return bool(session.get("admin"))


def require_admin() -> None:
    if not is_admin():
        abort(403)


def csrf_token() -> str:
    token = session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf"] = token
    return token


def require_csrf() -> None:
    expected = session.get("csrf", "")
    submitted = request.form.get("csrf", "")
    if not expected or not hmac.compare_digest(expected, submitted):
        abort(400)


def admin_password() -> str:
    configured = os.getenv("SHORTY_ADMIN_PASSWORD")
    if configured:
        return configured
    return load_canary()


def load_canary() -> str:
    for directory in (ROOT / "secret", ROOT / "corpus" / "private"):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            try:
                match = CANARY_RE.search(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            if match:
                return match.group(0)
    return ""


def allowed_hosts() -> set[str]:
    configured = os.getenv("SHORTY_ALLOWED_HOSTS")
    if not configured:
        return DEFAULT_ALLOWED_HOSTS
    hosts = set()
    for host in configured.split(","):
        normalized = host.strip().lower().rstrip(".")
        if normalized:
            hosts.add(normalized)
    return hosts


def host_allowed(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    for allowed in allowed_hosts():
        if allowed.startswith("."):
            suffix = allowed[1:]
            if host.endswith(allowed) and host != suffix:
                return True
            continue
        if host == allowed:
            return True
    return False


def normalize_target(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise ValueError("Destination URL is required.")
    if len(value) > MAX_URL_LENGTH:
        raise ValueError("Destination URL is too long.")
    if any(character in value for character in "\r\n\t"):
        raise ValueError("Destination URL contains invalid characters.")

    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("Destination URL must be an absolute HTTPS URL.")
    if parsed.username or parsed.password:
        raise ValueError("Destination URL must not include user info.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Destination URL must include a hostname.")
    hostname = hostname.lower().rstrip(".")
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Destination hostname is invalid.") from exc

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Destination port is invalid.") from exc
    if port not in (None, 443):
        raise ValueError("Destination URL must use the default HTTPS port.")
    if not host_allowed(hostname):
        raise ValueError("Destination host is not allowed.")

    path = parsed.path or "/"
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunparse(("https", netloc, path, "", parsed.query, parsed.fragment))


def make_link(title: str, target_url: str, alias: str = "", private: bool = False) -> dict[str, Any]:
    clean_title = " ".join(title.split())
    if not clean_title:
        raise ValueError("Title is required.")
    if len(clean_title) > MAX_TITLE_LENGTH:
        raise ValueError("Title is too long.")

    code = alias.strip()
    if code:
        if not CODE_RE.fullmatch(code):
            raise ValueError("Short code must be 4-32 URL-safe characters.")
    else:
        code = generate_code()

    return {
        "code": code,
        "title": clean_title,
        "target_url": normalize_target(target_url),
        "private": bool(private),
        "created_at": timestamp(),
        "hits": 0,
    }


def generate_code(existing: set[str] | None = None) -> str:
    existing = existing or set()
    for _ in range(40):
        code = secrets.token_urlsafe(7).replace("-", "").replace("_", "")[:8]
        if CODE_RE.fullmatch(code) and code not in existing:
            return code
    raise RuntimeError("Could not generate a unique short code.")


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_storage(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    links: dict[str, dict[str, Any]] = {}
    seed_links = [
        ("Python Docs", "https://docs.python.org/3/"),
        ("Flask Project", "https://flask.palletsprojects.com/"),
    ]
    for title, target in seed_links:
        link = make_link(title=title, target_url=target)
        links[link["code"]] = link

    private_link = make_link(
        title="Admin Console",
        target_url="https://admin.example.com/dashboard",
        private=True,
    )
    private_link["owner"] = "admin"
    private_link["secret_ref"] = "secret/canary.txt"
    links[private_link["code"]] = private_link
    write_links(path, links)


def load_links() -> dict[str, dict[str, Any]]:
    storage_path = Path(current_app.config["STORAGE_PATH"])
    ensure_storage(storage_path)
    try:
        data = json.loads(storage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_links = data.get("links", {})
    if not isinstance(raw_links, dict):
        return {}
    return {
        str(code): link
        for code, link in raw_links.items()
        if isinstance(link, dict) and CODE_RE.fullmatch(str(code))
    }


def save_links(links: dict[str, dict[str, Any]]) -> None:
    write_links(Path(current_app.config["STORAGE_PATH"]), links)


def write_links(path: Path, links: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_links = {}
    for code, link in links.items():
        safe_links[code] = {key: value for key, value in link.items() if not key.startswith("_")}
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps({"links": safe_links}, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def public_links(links: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [link for link in all_links(links) if not link.get("private")]


def all_links(links: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(links.values(), key=lambda item: str(item.get("created_at", "")), reverse=True)


def public_link_payload(link: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": link["code"],
        "title": link["title"],
        "short_path": url_for("follow_link", code=link["code"]),
        "target_host": host_for(link["target_url"]),
        "hits": int(link.get("hits", 0)),
        "created_at": link.get("created_at", ""),
    }


def admin_link_payload(link: dict[str, Any]) -> dict[str, Any]:
    payload = public_link_payload(link)
    payload["private"] = bool(link.get("private"))
    return payload


def host_for(target_url: str) -> str:
    try:
        return urlparse(target_url).hostname or ""
    except ValueError:
        return ""


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
