@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -I -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 goto use_py
)
where python >nul 2>nul
if not errorlevel 1 (
  python -I -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 goto use_python
)
echo Python 3.11 or newer was not found. Install it from python.org, then retry.
echo This package does not download/install Python or dependencies automatically.
exit /b 1
:use_py
py -3 -I %*
exit /b %errorlevel%
:use_python
python -I %*
exit /b %errorlevel%
