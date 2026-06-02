from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("flask")

from app import create_app


CSRF_RE = re.compile(rb'name="csrf" value="([^"]+)"')


@pytest.fixture
def storage_path(tmp_path: Path) -> Path:
    return tmp_path / "links.json"


@pytest.fixture
def client(storage_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SHORTY_ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv(
        "SHORTY_ALLOWED_HOSTS",
        "docs.python.org,flask.palletsprojects.com,example.com,.example.com",
    )
    app = create_app(storage_path)
    app.config.update(TESTING=True)
    return app.test_client()


def read_links(storage_path: Path) -> dict[str, dict]:
    return json.loads(storage_path.read_text(encoding="utf-8"))["links"]


def csrf_for(client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_RE.search(response.data)
    assert match
    return match.group(1).decode("ascii")


def test_public_link_redirects_to_allowed_https_target(client):
    response = client.post(
        "/api/links",
        json={
            "title": "Tutorial",
            "target_url": "https://docs.python.org/3/tutorial/",
            "alias": "pydocs",
        },
    )

    assert response.status_code == 201
    short_path = response.get_json()["short_path"]
    redirect_response = client.get(short_path)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["Location"] == "https://docs.python.org/3/tutorial/"


@pytest.mark.parametrize(
    "target_url",
    [
        "http://docs.python.org/3/",
        "javascript:alert(1)",
        "https://evil.example.net/login",
        "https://docs.python.org.evil.example.net/",
        "https://user:pass@docs.python.org/3/",
    ],
)
def test_rejects_open_redirect_targets(client, target_url: str):
    response = client.post(
        "/api/links",
        json={"title": "Bad target", "target_url": target_url},
    )

    assert response.status_code == 400


def test_private_admin_link_is_not_enumerable_without_login(client, storage_path: Path):
    client.get("/api/links")
    links = read_links(storage_path)
    private_code = next(code for code, link in links.items() if link.get("private"))

    public_response = client.get("/api/links")
    public_codes = {link["code"] for link in public_response.get_json()["links"]}
    assert private_code not in public_codes
    assert client.get(f"/u/{private_code}").status_code == 404

    token = csrf_for(client, "/login")
    login_response = client.post(
        "/login",
        data={"password": "test-admin-pass", "csrf": token},
    )
    assert login_response.status_code == 302

    admin_response = client.get("/api/admin/links")
    admin_codes = {link["code"] for link in admin_response.get_json()["links"]}
    assert private_code in admin_codes

    follow_response = client.get(f"/u/{private_code}")
    assert follow_response.status_code == 302
    assert follow_response.headers["Location"] == "https://admin.example.com/dashboard"


def test_user_title_is_escaped_in_html(client):
    response = client.post(
        "/api/links",
        json={
            "title": "<script>alert(1)</script>",
            "target_url": "https://docs.python.org/3/",
            "alias": "escape1",
        },
    )
    assert response.status_code == 201

    page = client.get("/")
    assert b"<script>alert(1)</script>" not in page.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page.data
