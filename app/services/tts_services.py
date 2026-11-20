import os
import time
import uuid
from pathlib import Path
from gtts import gTTS
from backend.app.config import settings

class TTSService:
    def __init__(self, output_dir: Path = None):
        self.output_dir = Path(output_dir or settings.TEMP_AUDIO_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_old_files(self, max_age_seconds: int = 3600):
        """Delete temporary audio files older than max_age_seconds."""
        now = time.time()
        for f in self.output_dir.glob("*.mp3"):
            try:
                if f.name == "test.mp3":
                    continue
                if now - f.stat().st_mtime > max_age_seconds:
                    f.unlink(missing_ok=True)
            except Exception:
                pass

    def text_to_speech(self, text: str, lang: str = "hi") -> dict:
        """
        Converts text into an MP3 audio file.
        Returns dictionary with filepath and filename.
        Gracefully handles network offline/timeout.
        """
        if not text or not text.strip():
            text = "Kripya dobara puchiye, mujhe jawab nahi mila."

        # Periodic cleanup of old audio files
        self.clean_old_files()

        filename = f"resp_{uuid.uuid4().hex[:8]}.mp3"
        file_path = self.output_dir / filename

        # Clean text slightly (remove markdown symbols that sound weird in TTS)
        tts_text = text.replace("*", "").replace("#", "").replace("`", "")
        if len(tts_text) > 400:
            tts_text = tts_text[:400] + "..."

        try:
            tts = gTTS(text=tts_text, lang=lang, slow=False, timeout=5)
            tts.save(str(file_path))
            return {
                "filename": filename,
                "file_path": str(file_path),
                "audio_url": f"/api/audio/{filename}"
            }
        except Exception as e:
            print(f"[TTS Warning] gTTS failed (network issue or offline): {e}")
            return {
                "filename": None,
                "file_path": None,
                "audio_url": None
            }

tts_service = TTSService()
