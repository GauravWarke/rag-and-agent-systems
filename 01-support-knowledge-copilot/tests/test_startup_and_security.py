"""Regression tests for the 2026-09 review of app/main.py.

- lifespan must be passed to FastAPI(), or the corpus is never indexed
  and every /ask retrieves from an empty index.
- /docs and /redoc need a relaxed CSP for their CDN assets; JSON routes keep
  the strict one.
- The rate-limit key only trusts X-Forwarded-For up to the configured hops.
"""
import re

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main
from app.main import app


def test_lifespan_is_wired_into_the_app():
    # FastAPI stores the handler as-is when it is passed, and substitutes a
    # no-op default when it is not. Identity is the precise check.
    assert app.router.lifespan_context is main.lifespan, (
        "app/main.py defines lifespan() but does not pass it to FastAPI(); "
        "startup will never index the corpus"
    )


def _external_hosts(html: str) -> set[str]:
    return set(re.findall(r'(?:src|href)=["\'](https?://[^/"\']+)', html))


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_docs_csp_allows_every_asset_the_page_loads(path):
    with TestClient(app) as client:
        r = client.get(path)
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    missing = {h for h in _external_hosts(r.text) if h not in csp}
    assert not missing, f"{path} loads {missing} but the CSP does not allow them: {csp}"


def test_api_routes_keep_the_strict_csp():
    with TestClient(app) as client:
        r = client.get("/health")
    csp = r.headers["content-security-policy"]
    assert csp.startswith("default-src 'none'")
    assert "script-src" not in csp


def _request(peer: str = "10.0.0.9", forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 5555)})


def test_client_key_ignores_forwarded_for_by_default(monkeypatch):
    monkeypatch.setattr(main, "_TRUSTED_PROXY_HOPS", 0)
    assert main._client_key(_request(forwarded="6.6.6.6")) == "10.0.0.9"


def test_client_key_uses_the_address_our_proxy_appended(monkeypatch):
    monkeypatch.setattr(main, "_TRUSTED_PROXY_HOPS", 1)
    # The client can prepend anything; only the last entry came from our proxy.
    assert main._client_key(_request(forwarded="6.6.6.6, 203.0.113.7")) == "203.0.113.7"


def test_client_key_falls_back_when_header_is_shorter_than_hops(monkeypatch):
    monkeypatch.setattr(main, "_TRUSTED_PROXY_HOPS", 2)
    assert main._client_key(_request(forwarded="203.0.113.7")) == "10.0.0.9"
