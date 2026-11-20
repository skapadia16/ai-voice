import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
streamlit_config_dir = PROJECT_ROOT / ".streamlit"

# Configure environment for clean Streamlit execution
os.environ["STREAMLIT_CONFIG_DIR"] = str(streamlit_config_dir)
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"

# Setup ffmpeg path for Whisper
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

python_exe = PROJECT_ROOT / "backend" / "venv" / "Scripts" / "python.exe"
app_file = PROJECT_ROOT / "streamlit_app.py"

if __name__ == "__main__":
    print("=" * 60)
    print("🎙️  STARTING STREAMLIT VOICE ASSISTANT")
    print("=" * 60)
    print("📍 URL: http://127.0.0.1:8501")
    print("=" * 60)
    
    cmd = [
        str(python_exe),
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false"
    ]
    subprocess.run(cmd, env=os.environ)
