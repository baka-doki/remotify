import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from app.db import (
    add_message,
    create_conversation,
    get_conversation,
    get_messages,
    init_db,
    list_conversations,
    maybe_set_title,
)

load_dotenv()

TOKEN = os.getenv("REMOTIFY_TOKEN", "change-me")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-transcribe")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))
MAX_AUDIO_BYTES = 25 * 1024 * 1024

app = FastAPI(title="Remotify ChatGPT")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
init_db()


class ChatRequest(BaseModel):
    text: str


class NewConversationRequest(BaseModel):
    model: str | None = None


def get_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured on this computer.",
        )
    return OpenAI()


def validate_token(request: Request) -> None:
    supplied = request.headers.get("x-remotify-token") or request.query_params.get("token")
    if not supplied or supplied != TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return Path("app/static/index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health(request: Request):
    validate_token(request)
    return {
        "status": "ok",
        "model": MODEL,
        "transcription_model": TRANSCRIPTION_MODEL,
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/conversations")
def conversations(request: Request):
    validate_token(request)
    return {"conversations": list_conversations()}


@app.post("/api/conversations")
def new_conversation(payload: NewConversationRequest, request: Request):
    validate_token(request)
    client = get_client()
    model = (payload.model or MODEL).strip()
    remote = client.conversations.create(metadata={"source": "remotify"})
    conversation = create_conversation(remote.id, model)
    return {"conversation": conversation}


@app.get("/api/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, request: Request):
    validate_token(request)
    conversation = get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation": {
            "id": conversation["id"],
            "title": conversation["title"],
            "model": conversation["model"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
        },
        "messages": get_messages(conversation_id),
    }


@app.post("/api/conversations/{conversation_id}/chat")
def chat(conversation_id: str, payload: ChatRequest, request: Request):
    validate_token(request)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")

    conversation = get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    client = get_client()
    add_message(conversation_id, "user", text)
    maybe_set_title(conversation_id, text)

    def event_stream():
        collected: list[str] = []
        try:
            stream = client.responses.create(
                model=conversation["model"],
                conversation=conversation["openai_conversation_id"],
                input=[{"role": "user", "content": text}],
                stream=True,
            )
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        collected.append(delta)
                        yield sse("delta", {"text": delta})
                elif event_type == "response.completed":
                    response = getattr(event, "response", None)
                    response_id = getattr(response, "id", None) if response else None
                    yield sse("meta", {"response_id": response_id})
                elif event_type == "error":
                    message = getattr(event, "message", "OpenAI streaming error")
                    yield sse("error", {"message": message})

            assistant_text = "".join(collected).strip()
            if assistant_text:
                add_message(conversation_id, "assistant", assistant_text)
            yield sse("done", {"ok": True})
        except Exception as exc:
            yield sse("error", {"message": str(exc)})
            yield sse("done", {"ok": False})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/transcribe")
def transcribe(request: Request, audio: UploadFile = File(...)):
    validate_token(request)
    client = get_client()

    raw = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25 MB")

    filename = audio.filename or "recording.webm"
    suffix = Path(filename).suffix or ".webm"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(raw)
            temp_path = temp.name

        with open(temp_path, "rb") as handle:
            result = client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=handle,
                prompt="Natural Chinese conversation. Preserve English product names and technical terms when spoken.",
            )
        return {"text": result.text}
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
