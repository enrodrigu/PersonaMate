from fastapi import FastAPI
from pydantic import BaseModel
from core import build_graph, chat_once

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


# Build the langgraph graph and config at startup
graph, config = build_graph()


@app.get("/")
def read_root():
    return {"status": "ok", "service": "PersonaMate backend"}


@app.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message
    print(f"User input received: {user_input}")  # Debugging log
    response_text = chat_once(user_input, graph, config)
    return {"response": response_text}