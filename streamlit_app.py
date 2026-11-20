import os
import sys
import uuid
import tempfile
from pathlib import Path

# Add project root to sys.path and configure Streamlit locally
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

local_streamlit_dir = PROJECT_ROOT / ".streamlit"
os.environ["STREAMLIT_CONFIG_DIR"] = str(local_streamlit_dir)
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

import streamlit as st
from audio_recorder_streamlit import audio_recorder

from backend.app.config import settings
from backend.app.services.stt_services import stt_service
from backend.app.services.rag_services import rag_service
from backend.app.services.tts_services import tts_service

# Page Configuration
st.set_page_config(
    page_title="Voice Assistant RAG",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Sleek Theme
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(236, 72, 153, 0.06) 0%, transparent 40%);
    }
    
    /* Header Container */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #6366f1, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Voice Recording Box */
    .voice-box {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    /* Source Pill */
    .source-tag {
        display: inline-block;
        background: rgba(6, 182, 212, 0.15);
        border: 1px solid rgba(6, 182, 212, 0.3);
        color: #06b6d4;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_recorded_audio" not in st.session_state:
    st.session_state.last_recorded_audio = None

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 📚 Knowledge Base")
    st.caption("Upload documents to build your custom vector database.")

    # File Uploader
    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        help="Upload PDF, TXT or Markdown files"
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = settings.DOCUMENTS_DIR / uploaded_file.name
            if not file_path.exists():
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                with st.spinner(f"Indexing '{uploaded_file.name}'..."):
                    chunks = rag_service.add_document(file_path)
                    st.success(f"Added {uploaded_file.name} ({chunks} chunks)")

    # Current Document List
    st.markdown("#### 📄 Indexed Documents")
    docs = rag_service.get_indexed_documents()
    if docs:
        for doc in docs:
            col_doc, col_del = st.columns([4, 1])
            with col_doc:
                st.write(f"• **{doc['filename']}** ({doc['size_bytes'] // 1024} KB)")
            with col_del:
                if st.button("🗑️", key=f"del_{doc['filename']}", help="Delete Document"):
                    rag_service.delete_document(doc['filename'])
                    st.rerun()
    else:
        st.info("Koi documents upload nahi hain.")

    st.markdown("---")

    # Re-index button
    if st.button("🔄 Re-index All Documents", use_container_width=True):
        with st.spinner("Re-indexing knowledge base..."):
            chunks_total = rag_service.reindex_all_documents()
            st.success(f"Successfully re-indexed {chunks_total} chunks!")

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    lang_choice = st.selectbox(
        "Voice Language (TTS/STT)",
        options=["hi", "en"],
        format_func=lambda x: "🇮🇳 Hindi (हिन्दी)" if x == "hi" else "🇬🇧 English"
    )

    auto_play = st.toggle("Auto-Play Voice Response", value=True)

    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # System Status
    st.markdown("---")
    st.markdown("#### ⚡ System Info")
    st.caption(f"Whisper Model: `{settings.WHISPER_MODEL_SIZE}`")
    st.caption(f"Embeddings: `all-MiniLM-L6-v2`")
    st.caption(f"Indexed Docs: `{len(docs)} files`")

# ----------------- MAIN CHAT & VOICE INTERFACE -----------------

st.markdown('<div class="main-title">🎙️ Audio RAG Voice Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Apne documents se aawaaz (voice) ya text mein baat karein. Whisper STT, ChromaDB RAG, aur gTTS Speech Assistant.</div>', unsafe_allow_html=True)

# Voice Recording Section
voice_col1, voice_col2 = st.columns([1, 2])

with voice_col1:
    st.markdown("**🎤 Mic se bolein:**")
    audio_bytes = audio_recorder(
        text="Click to Record",
        recording_color="#e63946",
        neutral_color="#6366f1",
        icon_size="2x",
        pause_threshold=2.0
    )

with voice_col2:
    audio_file_upload = st.file_uploader(
        "Ya audio file upload karein (.wav, .mp3, .webm)",
        type=["wav", "mp3", "webm", "m4a"],
        key="audio_upload_box"
    )

# Process Voice Input (Mic or Upload)
input_audio_to_process = None

if audio_bytes and audio_bytes != st.session_state.last_recorded_audio:
    st.session_state.last_recorded_audio = audio_bytes
    input_audio_to_process = ("mic", audio_bytes)
elif audio_file_upload:
    input_audio_to_process = ("upload", audio_file_upload.read())

if input_audio_to_process:
    src_type, raw_bytes = input_audio_to_process
    temp_audio_file = settings.TEMP_AUDIO_DIR / f"temp_{uuid.uuid4().hex[:8]}.webm"
    with open(temp_audio_file, "wb") as f:
        f.write(raw_bytes)

    with st.spinner("🎙️ Transcribing voice (OpenAI Whisper)..."):
        try:
            transcribed_text = stt_service.transcribe(str(temp_audio_file), language=lang_choice)
        except Exception as e:
            st.error(f"Whisper transcription error: {e}")
            transcribed_text = None
        finally:
            if temp_audio_file.exists():
                try:
                    temp_audio_file.unlink()
                except Exception:
                    pass

    if transcribed_text:
        # Save user message
        st.session_state.messages.append({
            "role": "user",
            "content": f"🎙️ {transcribed_text}",
            "type": "voice"
        })

        # Process with RAG
        with st.spinner("🧠 Searching documents & generating voice response..."):
            rag_res = rag_service.query_rag(transcribed_text)
            answer = rag_res["answer"]
            sources = rag_res.get("sources", [])

            # Generate TTS audio
            tts_res = tts_service.text_to_speech(answer, lang=lang_choice)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "audio_path": tts_res.get("file_path"),
                "sources": sources
            })
        st.rerun()

# Display Chat Messages
chat_container = st.container()
with chat_container:
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.write(msg["content"])
            
            # If assistant and has audio
            if msg["role"] == "assistant":
                audio_path = msg.get("audio_path")
                if audio_path and os.path.exists(audio_path):
                    st.audio(audio_path, format="audio/mp3")

                # If sources are present
                sources = msg.get("sources", [])
                if sources:
                    with st.expander("📚 Source References"):
                        for s in sources:
                            page_str = f" (Page {s['page']})" if s.get('page') else ""
                            st.markdown(f'<span class="source-tag">📄 {s["file"]}{page_str} - Distance: {s["score"]}</span>', unsafe_allow_html=True)

# Text Chat Input
user_text = st.chat_input("Apna sawaal yahan type karein...")
if user_text:
    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_text,
        "type": "text"
    })

    with st.spinner("🧠 Searching knowledge base & generating response..."):
        rag_res = rag_service.query_rag(user_text)
        answer = rag_res["answer"]
        sources = rag_res.get("sources", [])

        # Generate TTS audio
        tts_res = tts_service.text_to_speech(answer, lang=lang_choice)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "audio_path": tts_res.get("file_path"),
            "sources": sources
        })
    st.rerun()
