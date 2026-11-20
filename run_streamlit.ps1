$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$env:STREAMLIT_CONFIG_DIR = "$scriptDir\.streamlit"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_SERVER_HEADLESS = "false"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting Voice Assistant Streamlit App..." -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:8501" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

& "$scriptDir\backend\venv\Scripts\python.exe" -m streamlit run streamlit_app.py --server.port=8501 --server.address=127.0.0.1
