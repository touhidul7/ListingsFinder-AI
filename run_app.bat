@echo off
cd /d "%~dp0"
if not exist .venv call install.bat
call .venv\Scripts\activate.bat
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
