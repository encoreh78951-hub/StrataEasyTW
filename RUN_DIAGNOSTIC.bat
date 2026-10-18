@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 goto :directory_error
if not exist "diagnostics" mkdir "diagnostics"
if not exist "diagnostics" goto :log_error

echo Strata Easy TW - Windows startup diagnostic>"diagnostics\last-startup.log"
echo Date: %DATE% %TIME%>>"diagnostics\last-startup.log"
echo Current directory: %CD%>>"diagnostics\last-startup.log"
echo.>>"diagnostics\last-startup.log"
echo -- Files -->>"diagnostics\last-startup.log"
if exist "app.py" (echo app.py PRESENT>>"diagnostics\last-startup.log") else (echo app.py MISSING>>"diagnostics\last-startup.log")
if exist "bootstrap_windows.py" (echo bootstrap_windows.py PRESENT>>"diagnostics\last-startup.log") else (echo bootstrap_windows.py MISSING>>"diagnostics\last-startup.log")
if exist "LAUNCH_WINDOWS.bat" (echo LAUNCH_WINDOWS.bat PRESENT>>"diagnostics\last-startup.log") else (echo LAUNCH_WINDOWS.bat MISSING>>"diagnostics\last-startup.log")
echo.>>"diagnostics\last-startup.log"
echo -- Registered Python -->>"diagnostics\last-startup.log"
py -0p >>"diagnostics\last-startup.log" 2>&1
echo -- Python on PATH -->>"diagnostics\last-startup.log"
python --version >>"diagnostics\last-startup.log" 2>&1
where python >>"diagnostics\last-startup.log" 2>&1
where py >>"diagnostics\last-startup.log" 2>&1
echo.>>"diagnostics\last-startup.log"
echo -- Launcher output -->>"diagnostics\last-startup.log"
echo =======================================================
echo  Strata Easy TW - Startup Diagnostic (Fixed)
echo =======================================================
echo Please wait. First run may download Python dependencies.
echo The window stays open even if an error occurs.
echo.
if not exist "LAUNCH_WINDOWS.bat" goto :launcher_missing
rem IMPORTANT: call a RELATIVE ASCII filename, never expand the
rem absolute path containing percent signs, e.g. %%E5%%95...
call ".\LAUNCH_WINDOWS.bat" run >>"diagnostics\last-startup.log" 2>&1
set "RESULT=%errorlevel%"
goto :report
:launcher_missing
echo [ERROR] Missing LAUNCH_WINDOWS.bat>>"diagnostics\last-startup.log"
set "RESULT=2"
:report
echo Exit code: %RESULT%>>"diagnostics\last-startup.log"
echo.
echo -------------------- Full log ------------------------
type "diagnostics\last-startup.log"
echo -------------------- End log -------------------------
echo.
echo Saved to diagnostics\last-startup.log
echo Please send the log if troubleshooting is needed.
echo The log can contain your user name or folder paths.
popd
echo Press any key to close this console.
pause >nul
exit /b %RESULT%
:log_error
echo [ERROR] Cannot create diagnostics directory.
popd
pause
exit /b 2
:directory_error
echo [ERROR] Cannot access application directory.
pause
exit /b 3
