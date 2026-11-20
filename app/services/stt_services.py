import os
import sys
import shutil
from pathlib import Path
from backend.app.config import settings

# Setup ffmpeg path for whisper on Windows
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    # Ensure ffmpeg.exe exists in that directory
    ffmpeg_bin = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_bin):
        shutil.copyfile(ffmpeg_exe, ffmpeg_bin)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    print(f"Warning setting up ffmpeg: {e}")

# Also add venv Scripts to PATH
venv_scripts = str(Path(sys.executable).parent)
if venv_scripts not in os.environ.get("PATH", ""):
    os.environ["PATH"] = venv_scripts + os.pathsep + os.environ.get("PATH", "")

import whisper

class STTService:
    def __init__(self, model_size: str = None):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self._model = None

    @property
    def model(self):
        """Lazy load Whisper model on first use."""
        if self._model is None:
            print(f"[STT] Loading Whisper model ({self.model_size})...")
            self._model = whisper.load_model(self.model_size)
            print("[STT] Whisper model loaded successfully.")
        return self._model

    def transcribe(self, audio_path: str, language: str = None) -> str:
        """
        Transcribes audio file to text using Whisper.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"[STT] Transcribing audio file: {audio_path}")
        options = {}
        if language and language != "auto":
            options["language"] = language

        result = self.model.transcribe(audio_path, **options)
        transcribed_text = result.get("text", "").strip()
        print(f"[STT] Transcribed text: '{transcribed_text}'")
        return transcribed_text

# Global singleton
stt_service = STTService()
