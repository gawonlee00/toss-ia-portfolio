@echo off
cd /d "%~dp0"
title TOSS IA Portfolio v1.4.2 - Diagnostic
echo TOSS IA Portfolio v1.4.2 diagnostic launcher
echo.
call run_core.cmd
echo.
echo ----------------------------------------
echo Diagnostic finished.
echo Check run_log.txt in this folder.
echo ----------------------------------------
pause
