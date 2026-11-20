import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup ffmpeg path for Whisper
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

import uvicorn
from backend.app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🎙️  VOICE ASSISTANT RAG SYSTEM")
    print("=" * 60)
    print(f"📍 Server running at : http://{settings.HOST}:{settings.PORT}")
    print(f"📚 Documents Folder  : {settings.DOCUMENTS_DIR}")
    print(f"🧠 Vector Database   : {settings.VECTOR_DB_DIR}")
    print(f"🔊 Audio Output Dir  : {settings.TEMP_AUDIO_DIR}")
    print("=" * 60)
    print("👉 Browser me open karein: http://127.0.0.1:8000")
    print("=" * 60)
    
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE
    )
