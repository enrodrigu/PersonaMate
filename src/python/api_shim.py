from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from core import build_graph, chat_once
from dotenv import load_dotenv
import time

load_dotenv()

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "gpt-like"
    messages: List[Dict[str, Any]]

# Cache a compiled graph to avoid rebuilding per-request
_cached = {"graph": None, "config": None, "built_at": 0}

def get_cached_graph():
    # Rebuild if not present or older than 10 minutes
    ttl = 60 * 10
    now = time.time()
    if _cached["graph"] is None or now - _cached["built_at"] > ttl:
        g, cfg = build_graph()
        _cached["graph"] = g
        _cached["config"] = cfg
        _cached["built_at"] = now
    return _cached["graph"], _cached["config"]


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    messages = req.messages
    if not messages:
        raise HTTPException(status_code=400, detail="No messages")

    # Prefer the last user message
    user_text = None
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            user_text = m.get("content")
            break
    if user_text is None:
        # fallback to last element content
        last = messages[-1]
        if isinstance(last, dict):
            user_text = last.get("content")
        else:
            user_text = str(last)

    graph, config = get_cached_graph()
    assistant_text = chat_once(user_text, graph, config)

    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": assistant_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {},
    }



# Minimal OpenAI-compatible models endpoints so UIs (like OpenWebUI) can discover
# available models. We expose one local model `personamate-local` that maps to
# our internal LangGraph executable flow. You can extend this list to include
# real OpenAI models if you proxy to OpenAI.
_MODELS = [
    {
        "id": "personamate-local",
        "object": "model",
        "owned_by": "personamate",
        "permission": [],
        "root": "personamate-local",
    },
    {
        "id": "gpt-4o-mini",
        "object": "model",
        "owned_by": "openai",
        "permission": [],
        "root": "gpt-4o-mini",
    },
]


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": _MODELS}


@router.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    for m in _MODELS:
        if m["id"] == model_id:
            return m
    raise HTTPException(status_code=404, detail="Model not found")
