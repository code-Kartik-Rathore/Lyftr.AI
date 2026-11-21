"""Tests for the /health endpoint."""


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["keys_configured"] == 2
    assert body["cache_enabled"] is True


def test_health_keys_count_reflects_config(client, monkeypatch):
    """When keys change, health reflects the new count."""
    from app import config, routes
    monkeypatch.setattr(config.settings, "llm_api_keys", ["a", "b", "c"])
    # Also patch the reference imported into routes
    monkeypatch.setattr(routes, "settings", config.settings)
    resp = client.get("/health")
    assert resp.json()["keys_configured"] == 3
