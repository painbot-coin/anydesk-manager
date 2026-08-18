@echo off
REM Start AnyDesk Client in background (no console window)
REM No parameters needed - reads from config.json automatically
pythonw.exe client.py
REM If pythonw.exe is not available, use python with window minimized
REM start /min python client.py

