"""LiteLLM integration with key pool, auto-fallover, and caching."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import litellm
from litellm import completion
from litellm.caching.caching import Cache

from app.config import settings
from app.utils import should_simulate_failure

# ---------------------------------------------------------------------------
# Cache setup
# ---------------------------------------------------------------------------
litellm.cache = Cache(type="local")

# Silence litellm's own logging noise
litellm.suppress_debug_info = True


@dataclass
class LLMResult:
    reply: str
    resolution_source: str  # "LIVE_INFERENCE" or "LLM_CACHE"
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str]
    fallback_attempts: int


class AllProvidersUnavailableError(Exception):
    """Raised when every key in the pool has been exhausted."""


_RETRYABLE_STATUSES = {429, 500, 502, 503}


async def call_llm(
    messages: List[dict],
    model: Optional[str] = None,
    simulated_failures: Optional[Dict[str, int]] = None,
) -> LLMResult:
    """Call the LLM with key-pool fallover and caching.

    Parameters
    ----------
    messages:
        The full conversation (system + history + new user message).
    model:
        LiteLLM model identifier; defaults to settings.default_model.
    simulated_failures:
        Dict of key_id -> HTTP status to simulate (from X-Simulate-Failure).
    """
    model = model or settings.default_model
    keys = settings.llm_api_keys
    if not keys:
        raise AllProvidersUnavailableError("no API keys configured")

    fallback_attempts = 0
    last_error: Optional[Exception] = None

    for idx, api_key in enumerate(keys):
        key_id = f"key_{idx + 1}"

        # ----- Failure simulation -----
        if simulated_failures:
            sim_status = should_simulate_failure(key_id, simulated_failures)
            if sim_status is not None and sim_status in _RETRYABLE_STATUSES:
                fallback_attempts += 1
                continue

        # ----- Actual LLM call -----
        try:
            start = time.time()
            response = completion(
                model=model,
                messages=messages,
                api_key=api_key,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            # Detect cache hit
            cache_hit = False
            if hasattr(response, "_hidden_params") and response._hidden_params:
                cache_hit = response._hidden_params.get("cache_hit", False)

            reply_text = response.choices[0].message.content

            input_tokens = 0
            output_tokens = 0
            if response.usage:
                input_tokens = response.usage.prompt_tokens or 0
                output_tokens = response.usage.completion_tokens or 0

            return LLMResult(
                reply=reply_text,
                resolution_source="LLM_CACHE" if cache_hit else "LIVE_INFERENCE",
                model=model,
                latency_ms=elapsed_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                key_id=None if cache_hit else key_id,
                fallback_attempts=fallback_attempts,
            )
        except Exception as exc:
            last_error = exc
            status = getattr(exc, "status_code", None)
            if status in _RETRYABLE_STATUSES:
                fallback_attempts += 1
                continue
            # Non-retryable error → propagate immediately
            raise

    raise AllProvidersUnavailableError(
        f"all providers unavailable after {fallback_attempts} fallback attempt(s)"
    )
