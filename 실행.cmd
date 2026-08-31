@echo off
cd /d "%~dp0"
title TOSS IA Portfolio Web v1.4.2
call run_core.cmd
if errorlevel 1 (
  echo.
  echo The app could not be started.
  echo Run run.cmd and check run_log.txt.
  pause
)
