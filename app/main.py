import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.services.stt_services import stt_service
from backend.app.services.tts_services import tts_service
from backend.app.services.rag_services import rag_service

app = FastAPI(title="Voice Assistant RAG", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class TextQueryRequest(BaseModel):
    query: str
    lang: str = "hi"

# ----------------- Root / UI -----------------

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Voice RAG Assistant API is running.</h1>")

# ----------------- Status -----------------

@app.get("/api/status")
def get_system_status():
    docs = rag_service.get_indexed_documents()
    return {
        "status": "online",
        "documents_count": len(docs),
        "whisper_model": settings.WHISPER_MODEL_SIZE,
        "vector_db_ready": rag_service._vector_store is not None
    }

# ----------------- Voice & Text Chat -----------------

@app.post("/api/chat/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    lang: str = Form("hi")
):
    """
    Receives an audio file (e.g. from browser microphone),
    transcribes it using Whisper, retrieves relevant answers from RAG,
    and returns text + TTS audio.
    """
    temp_dir = Path(settings.TEMP_AUDIO_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded audio file
    input_audio_path = temp_dir / f"user_input_{audio.filename}"
    with open(input_audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
        # 1. Speech to Text (Whisper)
        transcribed_text = stt_service.transcribe(str(input_audio_path), language=lang if lang != "auto" else None)
        
        if not transcribed_text:
            return JSONResponse({
                "success": False,
                "user_query": "(Koi aawaaz sunai nahi di)",
                "answer": "Kripya dobara bolein, main sun nahi paya.",
                "audio_url": None,
                "sources": []
            })

        # 2. RAG retrieval & QA
        rag_result = rag_service.query_rag(transcribed_text)
        answer_text = rag_result["answer"]

        # 3. Text to Speech (gTTS)
        tts_result = tts_service.text_to_speech(answer_text, lang=lang)

        return {
            "success": True,
            "user_query": transcribed_text,
            "answer": answer_text,
            "audio_url": tts_result["audio_url"],
            "sources": rag_result.get("sources", [])
        }

    except Exception as e:
        print(f"[Error in chat_voice]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup uploaded input audio
        if input_audio_path.exists():
            try:
                input_audio_path.unlink()
            except Exception:
                pass

@app.post("/api/chat/text")
async def chat_text(req: TextQueryRequest):
    """
    Direct text question:
    Runs RAG query and generates TTS audio.
    """
    try:
        rag_result = rag_service.query_rag(req.query)
        answer_text = rag_result["answer"]
        tts_result = tts_service.text_to_speech(answer_text, lang=req.lang)

        return {
            "success": True,
            "user_query": req.query,
            "answer": answer_text,
            "audio_url": tts_result["audio_url"],
            "sources": rag_result.get("sources", [])
        }
    except Exception as e:
        print(f"[Error in chat_text]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Audio Serving -----------------

@app.get("/api/audio/{filename}")
def get_audio_file(filename: str):
    file_path = Path(settings.TEMP_AUDIO_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path=str(file_path), media_type="audio/mpeg")

# ----------------- Document Management -----------------

@app.get("/api/documents")
def list_documents():
    return {"documents": rag_service.get_indexed_documents()}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    docs_dir = Path(settings.DOCUMENTS_DIR)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = docs_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Index newly uploaded document
    chunks_count = rag_service.add_document(file_path)

    return {
        "success": True,
        "message": f"File '{file.filename}' uploaded and indexed ({chunks_count} chunks).",
        "filename": file.filename,
        "chunks": chunks_count
    }

@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    success = rag_service.delete_document(filename)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True, "message": f"Deleted {filename} and updated vector index."}

@app.post("/api/documents/reindex")
def reindex_documents():
    chunks = rag_service.reindex_all_documents()
    return {"success": True, "message": f"Knowledge base re-indexed successfully with {chunks} chunks."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG_MODE)
