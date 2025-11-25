from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core import build_graph, chat_once
from api_shim import router as shim_router
from tools_api import router as tools_router

app = FastAPI()

# Enable CORS for local OpenWebUI; adjust origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


# Build the langgraph graph and config at startup
graph, config = build_graph()

# Mount the OpenAI-compatible shim and tool endpoints
app.include_router(shim_router)
app.include_router(tools_router)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "PersonaMate backend"}


@app.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message
    print(f"User input received: {user_input}")  # Debugging log
    response_text = chat_once(user_input, graph, config)
    return {"response": response_text}