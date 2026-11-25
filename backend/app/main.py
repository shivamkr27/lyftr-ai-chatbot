import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import connect, initialize_database
from .schemas import ChatRequest
from .services.cache_service import configure_cache
from .services.fallback_service import parse_failure_header
from .services.llm_service import ProviderUnavailable, completion

settings = get_settings()
initialize_database(settings.database_url)
configure_cache(settings.cache_enabled)

app = FastAPI(
    title="Lyftr AI Chatbot",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@app.exception_handler(ProviderUnavailable)
async def provider_unavailable_handler(request: Request, exc: ProviderUnavailable):
    return JSONResponse(status_code=503, content={"detail": "all providers unavailable"})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health")
def health():
    connection = connect(settings.database_url)
    try:
        connection.execute("SELECT 1").fetchone()
    finally:
        connection.close()
    return {
        "status": "ok",
        "keys_configured": len(settings.llm_api_keys),
        "cache_enabled": settings.cache_enabled,
    }


def get_history(session_id: str) -> list[dict]:
    connection = connect(settings.database_url)
    try:
        rows = connection.execute(
            "SELECT role, content, metadata FROM messages "
            "WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    finally:
        connection.close()

    history = []
    for row in rows:
        history.append({"role": row["role"], "content": row["content"]})
    return history


def stored_history(session_id: str) -> list[dict]:
    connection = connect(settings.database_url)
    try:
        rows = connection.execute(
            "SELECT role, content, metadata FROM messages "
            "WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    finally:
        connection.close()

    messages = []
    for row in rows:
        item = {"role": row["role"], "content": row["content"]}
        if row["role"] == "assistant" and row["metadata"]:
            item["metadata"] = json.loads(row["metadata"])
        messages.append(item)
    return messages


@app.post("/chat")
def chat(payload: ChatRequest, x_simulate_failure: Optional[str] = Header(default=None)):
    key_ids = [f"key_{index}" for index in range(1, len(settings.llm_api_keys) + 1)]
    simulated = {}
    if settings.enable_failure_simulation:
        simulated = parse_failure_header(x_simulate_failure or "", key_ids)

    connection = connect(settings.database_url)
    try:
        if payload.system_prompt is not None:
            system_prompt = payload.system_prompt.strip()
        else:
            row = connection.execute(
                "SELECT system_prompt FROM session_prompts WHERE session_id = ?",
                (payload.session_id,),
            ).fetchone()
            system_prompt = row["system_prompt"] if row else "You are a helpful assistant."
    finally:
        connection.close()

    connection = connect(settings.database_url)
    try:
        rows = connection.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = ? AND role IN ('user', 'assistant') "
            "ORDER BY created_at ASC, id ASC",
            (payload.session_id,),
        ).fetchall()
    finally:
        connection.close()

    messages = []
    messages.append({"role": "system", "content": system_prompt})

    for row in rows:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": payload.message})

    try:
        result = completion(
            model=settings.llm_model,
            messages=messages,
            api_keys=settings.llm_api_keys,
            key_ids=key_ids,
            simulated_failures=simulated,
            cache_enabled=settings.cache_enabled,
        )
    except ProviderUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    if not result["reply"]:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    metadata = {
        "resolution_source": result["resolution_source"],
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "key_id": result["key_id"],
        "fallback_attempts": result["fallback_attempts"],
    }
    metadata_for_history = {
        "resolution_source": result["resolution_source"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }

    connection = connect(settings.database_url)
    try:
        if payload.system_prompt is not None:
            connection.execute(
                "INSERT INTO session_prompts (session_id, system_prompt, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "system_prompt=excluded.system_prompt, updated_at=excluded.updated_at",
                (payload.session_id, payload.system_prompt.strip(), iso_now()),
            )
        connection.execute(
            "INSERT INTO messages (session_id, role, content, metadata, created_at) "
            "VALUES (?, 'user', ?, NULL, ?)",
            (payload.session_id, payload.message, iso_now()),
        )
        connection.execute(
            "INSERT INTO messages (session_id, role, content, metadata, created_at) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            (
                payload.session_id,
                str(result["reply"]),
                json.dumps(metadata_for_history),
                iso_now(),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return {"session_id": payload.session_id, "reply": result["reply"], "metadata": metadata}


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    session_id = session_id.strip()
    if not session_id:
        raise HTTPException(status_code=404, detail="session not found")
    messages = stored_history(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "messages": messages}
