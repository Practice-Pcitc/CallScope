@echo off
setlocal
set "PYTHONUTF8=1"
set "HOOK_ROOT=%~dp0"
set "PYTHON_EXE=%HOOK_ROOT%..\backend\.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" "%HOOK_ROOT%prompt_hook.py"
) else (
  python "%HOOK_ROOT%prompt_hook.py"
)

rem The recorder is fail-open: it must never block or fail a Codex prompt.
exit /b 0
