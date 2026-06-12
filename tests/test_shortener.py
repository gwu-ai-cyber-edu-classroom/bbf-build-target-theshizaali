from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
def app(storage_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SHORTY_ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv(
        "SHORTY_ALLOWED_HOSTS",
        "docs.python.org,flask.palletsprojects.com,example.com,.example.com",
    )
    app = create_app(storage_path)
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
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


def test_concurrent_api_creates_persist_all_links(app, storage_path: Path):
    link_count = 30

    def create(index: int) -> int:
        with app.test_client() as worker:
            response = worker.post(
                "/api/links",
                json={
                    "title": f"Race {index}",
                    "target_url": "https://docs.python.org/3/",
                    "alias": f"race{index}",
                },
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(create, range(link_count)))

    assert statuses == [201] * link_count
    links = read_links(storage_path)
    assert {f"race{index}" for index in range(link_count)} <= set(links)


def test_concurrent_follows_preserve_hit_count(app, storage_path: Path):
    follow_count = 40
    with app.test_client() as client:
        response = client.post(
            "/api/links",
            json={
                "title": "Hit counter",
                "target_url": "https://docs.python.org/3/",
                "alias": "hitcount",
            },
        )
    assert response.status_code == 201

    def follow(_index: int) -> int:
        with app.test_client() as worker:
            return worker.get("/u/hitcount").status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(follow, range(follow_count)))

    assert statuses == [302] * follow_count
    assert read_links(storage_path)["hitcount"]["hits"] == follow_count


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
