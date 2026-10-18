@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
rem Use only ASCII in .bat files. GUI messages remain in Traditional Chinese.
rem This launcher must be called from its own directory (RUN_*.bat uses pushd).
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "APP_ARGS="
if /I "%~1"=="demo" set "APP_ARGS=--demo"
if /I "%~1"=="build" set "APP_ARGS=--build"
set "FOUND_PY="
if defined STRATA_GUIDE_PYTHON goto :custom_python
rem Prefer installed x64 CPython; Python 3.10.11 is fully supported.
for %%V in (3.12 3.13 3.11 3.10) do call :probe_py %%V
if defined FOUND_PY goto :use_py
python -c "import sys;sys.exit(0 if sys.implementation.name=='cpython' and (3,10)<=sys.version_info[:2]<=(3,13) and sys.maxsize>2**32 else 1)" >nul 2>nul
if not errorlevel 1 goto :use_python
python3 -c "import sys;sys.exit(0 if sys.implementation.name=='cpython' and (3,10)<=sys.version_info[:2]<=(3,13) and sys.maxsize>2**32 else 1)" >nul 2>nul
if not errorlevel 1 goto :use_python3

echo [ERROR] A supported 64-bit Python was not detected.
echo Supported: CPython 3.10, 3.11, 3.12, 3.13 (64-bit).
echo Try: py -0p
exit /b 1
:probe_py
if defined FOUND_PY exit /b 0
py -%~1 -c "import sys;sys.exit(0 if sys.implementation.name=='cpython' and (3,10)<=sys.version_info[:2]<=(3,13) and sys.maxsize>2**32 else 1)" >nul 2>nul
if not errorlevel 1 set "FOUND_PY=%~1"
exit /b 0
:use_py
echo [INFO] Using registered Python %FOUND_PY% x64.
py -%FOUND_PY% bootstrap_windows.py %APP_ARGS%
exit /b %errorlevel%
:use_python
echo [INFO] Using Python x64 from PATH.
python bootstrap_windows.py %APP_ARGS%
exit /b %errorlevel%
:use_python3
echo [INFO] Using python3 x64 from PATH.
python3 bootstrap_windows.py %APP_ARGS%
exit /b %errorlevel%
:custom_python
if not exist "%STRATA_GUIDE_PYTHON%" goto :bad_custom
"%STRATA_GUIDE_PYTHON%" -c "import sys;sys.exit(0 if sys.implementation.name=='cpython' and (3,10)<=sys.version_info[:2]<=(3,13) and sys.maxsize>2**32 else 1)" >nul 2>nul
if errorlevel 1 goto :bad_custom
"%STRATA_GUIDE_PYTHON%" bootstrap_windows.py %APP_ARGS%
exit /b %errorlevel%
:bad_custom
echo [ERROR] STRATA_GUIDE_PYTHON is missing or unsupported.
exit /b 1
