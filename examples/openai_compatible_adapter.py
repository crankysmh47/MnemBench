"""Minimal FastAPI adapter shape for MnemBench.

This is not a memory system. It shows the HTTP contract MnemBench expects from
a candidate agent server.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="MnemBench example adapter")


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    return ChatResponse(
        response=(
            "This example adapter received a message for "
            f"user={req.user_id}, session={req.session_id}: {req.message}"
        )
    )
