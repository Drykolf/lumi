@echo off
:: LUMI - Backend startup script
:: Runs the OLV server with uv. Keep this window open while Lumi is active.

cd /d "%~dp0..\.."
echo [LUMI] Starting backend server...
uv run run_server.py
pause
