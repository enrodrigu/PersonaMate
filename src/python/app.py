from fastapi import FastAPI
from pydantic import BaseModel
from core import graph, config
from utils.helper import _print_event

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def read_root():
    return {"status": "ok", "service": "PersonaMate backend"}


@app.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message
    print(f"User input received: {user_input}")  # Debugging log
    events = graph.stream(
        {"messages": ("user", user_input)}, config, stream_mode="values"
    )
    last_response = ""
    _printed = set()
    for event in events:
        response = _print_event(event, _printed)
        if response:
            last_response = response
    return {"response": last_response}


# For local development you can run:
# uvicorn src.python.app:app --host 0.0.0.0 --port 8000 --reload