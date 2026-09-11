@echo off
setlocal
title Delivery Operations Intelligence
cd /d "%~dp0.."
set "DELIVERY_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "DELIVERY_PYTHON=.venv\Scripts\python.exe"
if not exist "outputs\orders.parquet" (
  echo Private canonical outputs are missing. See docs\DATA_ACCESS.md.
  echo After obtaining authorized raw inputs, run:
  echo   %DELIVERY_PYTHON% -m delivery_ops run --data-dir private_data
  pause
  exit /b 1
)
echo Delivery Operations Intelligence
echo Open http://localhost:8503 in your browser.
echo Keep this window open. Press Ctrl+C to stop the server.
"%DELIVERY_PYTHON%" -m streamlit run v16\dashboard_v16.py --server.port 8503 --server.headless true --browser.gatherUsageStats false
pause
