"""Tests for the /chat endpoint."""

from unittest.mock import MagicMock, patch

import pytest


def _mock_litellm_response(content="Hello!", prompt_tokens=10, completion_tokens=5, cache_hit=False):
    """Build a mock object mimicking a LiteLLM ModelResponse."""
    msg = MagicMock()
    msg.content = content

    choice = MagicMock()
    choice.message = msg

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    resp._hidden_params = {"cache_hit": cache_hit}

    return resp


class TestChatBasic:
    """Basic chat request/response cycle."""

    @patch("app.llm_service.completion")
    def test_successful_chat(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("Paris is the capital.")
        resp = client.post("/chat", json={
            "session_id": "s-test",
            "message": "What is the capital of France?"
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "s-test"
        assert body["reply"] == "Paris is the capital."
        meta = body["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["model"] == "gemini/gemini-2.0-flash"
        assert meta["key_id"] == "key_1"
        assert meta["fallback_attempts"] == 0
        assert meta["input_tokens"] == 10
        assert meta["output_tokens"] == 5

    @patch("app.llm_service.completion")
    def test_chat_with_system_prompt(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("Sure!")
        resp = client.post("/chat", json={
            "session_id": "s-sys",
            "message": "Hello",
            "system_prompt": "You are a pirate."
        })
        assert resp.status_code == 200
        # Verify the system prompt was sent to litellm
        call_args = mock_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][0]
        # Find system message
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0]["content"] == "You are a pirate."


class TestChatValidation:
    """Validation error cases → 422."""

    def test_missing_session_id(self, client):
        resp = client.post("/chat", json={"message": "hi"})
        assert resp.status_code == 422

    def test_empty_session_id(self, client):
        resp = client.post("/chat", json={"session_id": "", "message": "hi"})
        assert resp.status_code == 422

    def test_missing_message(self, client):
        resp = client.post("/chat", json={"session_id": "s1"})
        assert resp.status_code == 422

    def test_empty_message(self, client):
        resp = client.post("/chat", json={"session_id": "s1", "message": "   "})
        assert resp.status_code == 422

    def test_message_too_long(self, client):
        resp = client.post("/chat", json={
            "session_id": "s1",
            "message": "a" * 4001
        })
        assert resp.status_code == 422

    def test_session_id_too_long(self, client):
        resp = client.post("/chat", json={
            "session_id": "x" * 129,
            "message": "hi"
        })
        assert resp.status_code == 422

    def test_malformed_json(self, client):
        resp = client.post("/chat", content=b"not json", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422


class TestChatCacheHit:
    """Cache hit detection."""

    @patch("app.llm_service.completion")
    def test_cache_hit_metadata(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("cached!", cache_hit=True)
        resp = client.post("/chat", json={
            "session_id": "s-cache",
            "message": "repeat"
        })
        assert resp.status_code == 200
        meta = resp.json()["metadata"]
        assert meta["resolution_source"] == "LLM_CACHE"
        assert meta["key_id"] is None
        assert meta["fallback_attempts"] == 0


class TestFailoverSimulation:
    """X-Simulate-Failure header tests."""

    @patch("app.llm_service.completion")
    def test_failover_to_key2(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("from key 2")
        resp = client.post(
            "/chat",
            json={"session_id": "s-fail", "message": "hi"},
            headers={"X-Simulate-Failure": "key_1=429"},
        )
        assert resp.status_code == 200
        meta = resp.json()["metadata"]
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1

    def test_all_keys_fail_returns_503(self, client):
        resp = client.post(
            "/chat",
            json={"session_id": "s-fail-all", "message": "hi"},
            headers={"X-Simulate-Failure": "*=429"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "all providers unavailable"

    @patch("app.llm_service.completion")
    def test_simulation_disabled_ignores_header(self, mock_completion, client, monkeypatch):
        """When ENABLE_FAILURE_SIMULATION is false, the header is ignored."""
        from app import config, routes
        monkeypatch.setattr(config.settings, "enable_failure_simulation", False)
        # Also patch the reference imported into routes
        monkeypatch.setattr(routes, "settings", config.settings)
        mock_completion.return_value = _mock_litellm_response("normal")
        resp = client.post(
            "/chat",
            json={"session_id": "s-no-sim", "message": "hi"},
            headers={"X-Simulate-Failure": "key_1=429"},
        )
        assert resp.status_code == 200
        # Should use key_1, not fall over
        assert resp.json()["metadata"]["key_id"] == "key_1"
        assert resp.json()["metadata"]["fallback_attempts"] == 0


class TestMultiTurn:
    """Multi-turn conversation history."""

    @patch("app.llm_service.completion")
    def test_history_sent_to_llm(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("First reply")
        client.post("/chat", json={"session_id": "s-multi", "message": "Hello"})

        mock_completion.return_value = _mock_litellm_response("Second reply")
        client.post("/chat", json={"session_id": "s-multi", "message": "Follow up"})

        # Second call should include history
        call_args = mock_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        # system + user1 + assistant1 + user2
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "First reply"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Follow up"
