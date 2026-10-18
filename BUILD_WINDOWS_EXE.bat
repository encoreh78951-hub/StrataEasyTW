@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 goto :directory_error
if not exist "LAUNCH_WINDOWS.bat" goto :missing
call ".\LAUNCH_WINDOWS.bat" build
set "RESULT=%errorlevel%"
popd
if not "%RESULT%"=="0" echo [ERROR] Build failed with code %RESULT%.
echo Press any key to close this console.
pause >nul
exit /b %RESULT%
:missing
echo [ERROR] Missing LAUNCH_WINDOWS.bat.
popd
pause
exit /b 2
:directory_error
echo [ERROR] Cannot access application directory.
pause
exit /b 3
