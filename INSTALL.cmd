@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
call "%~dp0_python.cmd" "%~dp0install_skill.py"
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" echo Stopped. Read the message above.
pause
exit /b %RC%
