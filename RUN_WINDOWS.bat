@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 goto :directory_error
if not exist "app.py" goto :missing
if not exist "LAUNCH_WINDOWS.bat" goto :missing

echo =======================================================
echo  Strata Easy TW - Windows Launcher (Fixed)
echo =======================================================
echo Starting the Traditional Chinese guide...
echo.
call ".\LAUNCH_WINDOWS.bat" run
set "RESULT=%errorlevel%"
echo.
if "%RESULT%"=="0" goto :success
echo [ERROR] Exit code: %RESULT%
echo To get the full error, run RUN_DIAGNOSTIC.bat.
goto :finish
:success
echo [INFO] The guide window has closed.
:finish
popd
echo Press any key to close this console.
pause >nul
exit /b %RESULT%
:missing
echo [ERROR] Missing app.py or LAUNCH_WINDOWS.bat.
echo Extract the entire ZIP to a folder before starting.
popd
pause
exit /b 2
:directory_error
echo [ERROR] Cannot access application directory.
pause
exit /b 3
