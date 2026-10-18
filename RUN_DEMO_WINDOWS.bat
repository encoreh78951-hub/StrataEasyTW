@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 goto :directory_error
if not exist "app.py" goto :missing
if not exist "LAUNCH_WINDOWS.bat" goto :missing

echo =======================================================
echo  Strata Easy TW - OFFLINE DEMO (No Model Install)
echo =======================================================
call ".\LAUNCH_WINDOWS.bat" demo
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" goto :success
echo [ERROR] Exit code: %RESULT%
echo Run RUN_DIAGNOSTIC.bat to save a detailed log.
goto :finish
:success
echo [INFO] Offline demo has closed.
:finish
popd
echo Press any key to close this console.
pause >nul
exit /b %RESULT%
:missing
echo [ERROR] Missing application files. Extract the full ZIP.
popd
pause
exit /b 2
:directory_error
echo [ERROR] Cannot access application directory.
pause
exit /b 3
