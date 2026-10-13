@echo off
rem Starts Montra and opens it in your browser. Close this window to stop it.
title Montra
cd /d "%~dp0"
uv run streamlit run app.py --server.address localhost
rem If the app could not start, keep the window open so the error can be read.
if errorlevel 1 pause
