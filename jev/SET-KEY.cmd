@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
call "%~dp0_python.cmd" "%~dp0scripts\jev.py" set-key
set "RC=%errorlevel%"
echo.
pause
exit /b %RC%
