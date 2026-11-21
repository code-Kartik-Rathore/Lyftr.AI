"""Pydantic models for request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str
    system_prompt: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        if len(trimmed) > 4000:
            raise ValueError("message must be at most 4000 characters")
        return trimmed


class ChatMetadata(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str]
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class MessageEntry(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = None


class SessionHistory(BaseModel):
    session_id: str
    messages: List[MessageEntry]


class HealthResponse(BaseModel):
    status: str
    keys_configured: int
    cache_enabled: bool
