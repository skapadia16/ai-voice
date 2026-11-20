@echo off
title Voice Assistant Streamlit
cd /d "%~dp0"
set STREAMLIT_CONFIG_DIR=%~dp0.streamlit
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=false

echo ========================================================
echo   Starting Voice Assistant RAG Streamlit App...
echo ========================================================
echo   URL: http://127.0.0.1:8501
echo ========================================================

backend\venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port=8501 --server.address=127.0.0.1
pause
