"""API route handlers."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.database import get_session_messages, save_message, session_exists
from app.llm_service import AllProvidersUnavailableError, call_llm
from app.models import (
    ChatMetadata,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MessageEntry,
    SessionHistory,
)
from app.utils import parse_failure_header

router = APIRouter()

# In-memory store for per-session system prompts
_session_system_prompts: dict[str, str] = {}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        keys_configured=len(settings.llm_api_keys),
        cache_enabled=True,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure"),
) -> ChatResponse:
    # Determine system prompt
    system_prompt = request.system_prompt
    if system_prompt is None:
        system_prompt = _session_system_prompts.get(
            request.session_id, settings.default_system_prompt
        )
    # Persist the system prompt for this session for future turns
    _session_system_prompts[request.session_id] = system_prompt

    # Build the full message list
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Fetch existing history
    history = await get_session_messages(request.session_id)
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})

    # Add the new user message
    messages.append({"role": "user", "content": request.message})

    # Parse simulation header
    simulated_failures = None
    if settings.enable_failure_simulation and x_simulate_failure:
        simulated_failures = parse_failure_header(x_simulate_failure)

    # Call LLM
    try:
        result = await call_llm(
            messages=messages,
            simulated_failures=simulated_failures,
        )
    except AllProvidersUnavailableError:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    # Build metadata for storage (subset)
    assistant_metadata = {
        "resolution_source": result.resolution_source,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }

    # Persist user and assistant messages
    await save_message(request.session_id, "user", request.message)
    await save_message(
        request.session_id,
        "assistant",
        result.reply,
        metadata=assistant_metadata,
    )

    return ChatResponse(
        session_id=request.session_id,
        reply=result.reply,
        metadata=ChatMetadata(
            resolution_source=result.resolution_source,
            model=result.model,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            key_id=result.key_id,
            fallback_attempts=result.fallback_attempts,
        ),
    )


@router.get("/sessions/{session_id}/messages", response_model=SessionHistory)
async def get_session(session_id: str) -> SessionHistory:
    exists = await session_exists(session_id)
    if not exists:
        raise HTTPException(status_code=404, detail="session not found")

    rows = await get_session_messages(session_id)
    messages = []
    for row in rows:
        entry = MessageEntry(
            role=row["role"],
            content=row["content"],
            metadata=row.get("metadata"),
        )
        messages.append(entry)

    return SessionHistory(session_id=session_id, messages=messages)
