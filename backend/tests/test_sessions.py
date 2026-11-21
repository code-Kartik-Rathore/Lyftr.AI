"""Tests for the /sessions/{session_id}/messages endpoint."""

from unittest.mock import MagicMock, patch


def _mock_litellm_response(content="Hello!", prompt_tokens=10, completion_tokens=5, cache_hit=False):
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


class TestGetSession:

    def test_unknown_session_returns_404(self, client):
        resp = client.get("/sessions/nonexistent/messages")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "session not found"

    @patch("app.llm_service.completion")
    def test_returns_history_in_order(self, mock_completion, client):
        mock_completion.return_value = _mock_litellm_response("Reply 1", prompt_tokens=20, completion_tokens=8)
        client.post("/chat", json={"session_id": "s-hist", "message": "First"})

        mock_completion.return_value = _mock_litellm_response("Reply 2", prompt_tokens=30, completion_tokens=12)
        client.post("/chat", json={"session_id": "s-hist", "message": "Second"})

        resp = client.get("/sessions/s-hist/messages")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "s-hist"
        msgs = body["messages"]
        assert len(msgs) == 4  # user, assistant, user, assistant

        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "First"
        assert msgs[0].get("metadata") is None

        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "Reply 1"
        assert msgs[1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert msgs[1]["metadata"]["input_tokens"] == 20
        assert msgs[1]["metadata"]["output_tokens"] == 8

        assert msgs[2]["role"] == "user"
        assert msgs[2]["content"] == "Second"

        assert msgs[3]["role"] == "assistant"
        assert msgs[3]["content"] == "Reply 2"

    @patch("app.llm_service.completion")
    def test_no_system_prompt_in_history(self, mock_completion, client):
        """System prompt should NOT appear in returned history."""
        mock_completion.return_value = _mock_litellm_response("Sure!")
        client.post("/chat", json={
            "session_id": "s-nosys",
            "message": "hi",
            "system_prompt": "Be a pirate"
        })
        resp = client.get("/sessions/s-nosys/messages")
        msgs = resp.json()["messages"]
        for m in msgs:
            assert m["role"] != "system"

    @patch("app.llm_service.completion")
    def test_failed_llm_does_not_persist(self, mock_completion, client):
        """If LLM call fails, messages should NOT be saved."""
        from app.llm_service import AllProvidersUnavailableError

        # First make a *successful* call so the session exists
        mock_completion.return_value = _mock_litellm_response("ok")
        client.post("/chat", json={"session_id": "s-fail-persist", "message": "good"})

        # Now simulate all keys failing via header
        resp = client.post(
            "/chat",
            json={"session_id": "s-fail-persist", "message": "this should fail"},
            headers={"X-Simulate-Failure": "*=429"},
        )
        assert resp.status_code == 503

        # History should only have the successful exchange
        hist_resp = client.get("/sessions/s-fail-persist/messages")
        assert len(hist_resp.json()["messages"]) == 2  # user + assistant from first call
