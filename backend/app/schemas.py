from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str
    system_prompt: Optional[str] = None

    @field_validator("session_id")
    @classmethod
    def trim_session_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("session_id must not be empty")
        return value

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        if len(value) > 4000:
            raise ValueError("message must be at most 4000 characters")
        return value
