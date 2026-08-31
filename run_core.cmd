@echo off
setlocal EnableExtensions
cd /d "%~dp0"

> "run_log.txt" echo ===== TOSS IA Portfolio v1.4.2 diagnostic log =====
>>"run_log.txt" echo Folder: %CD%
>>"run_log.txt" echo Date: %DATE% %TIME%
>>"run_log.txt" echo.

echo [1] Checking app files...
>>"run_log.txt" echo [1] Checking app files...
for %%F in (app.py requirements.txt needs_engine.py config.py statistical_risk.py money_utils.py) do (
  if exist "%%F" (
    echo   OK: %%F
    >>"run_log.txt" echo OK: %%F
  ) else (
    echo   MISSING: %%F
    >>"run_log.txt" echo MISSING: %%F
  )
)

echo.
echo [2] Looking for Python...
>>"run_log.txt" echo.
>>"run_log.txt" echo [2] Looking for Python...

set "PYMODE="

python --version >>"run_log.txt" 2>&1
if not errorlevel 1 set "PYMODE=python"

if not defined PYMODE (
  py -3 --version >>"run_log.txt" 2>&1
  if not errorlevel 1 set "PYMODE=py"
)

if not defined PYMODE (
  echo ERROR: Python 3 was not found.
  >>"run_log.txt" echo ERROR: Python 3 was not found.
  echo.
  echo Install Python 3 and check "Add Python to PATH".
  goto :END
)

if "%PYMODE%"=="python" (
  set "PYCMD=python"
) else (
  set "PYCMD=py -3"
)

echo   Python command: %PYCMD%
>>"run_log.txt" echo Python command: %PYCMD%

echo.
echo [3] Preparing virtual environment...
>>"run_log.txt" echo.
>>"run_log.txt" echo [3] Preparing virtual environment...

if not exist ".venv\Scripts\python.exe" (
  echo   Creating .venv ...
  >>"run_log.txt" echo Creating .venv ...
  %PYCMD% -m venv .venv >>"run_log.txt" 2>&1
  if errorlevel 1 (
    echo ERROR: Failed to create .venv
    >>"run_log.txt" echo ERROR: Failed to create .venv
    goto :END
  )
)

set "VPY=.venv\Scripts\python.exe"

echo.
echo [4] Checking pip...
>>"run_log.txt" echo.
>>"run_log.txt" echo [4] Checking pip...
"%VPY%" -m pip --version >>"run_log.txt" 2>&1
if errorlevel 1 (
  echo ERROR: pip is unavailable.
  >>"run_log.txt" echo ERROR: pip is unavailable.
  goto :END
)

echo.
echo [5] Checking required packages...
>>"run_log.txt" echo.
>>"run_log.txt" echo [5] Checking required packages...
"%VPY%" -c "import streamlit, pandas, plotly" >>"run_log.txt" 2>&1
if errorlevel 1 (
  echo   Installing packages. Internet may be required...
  >>"run_log.txt" echo Installing packages...
  "%VPY%" -m pip install -r requirements.txt >>"run_log.txt" 2>&1
  if errorlevel 1 (
    echo ERROR: Package installation failed.
    >>"run_log.txt" echo ERROR: Package installation failed.
    goto :END
  )
)

echo.
echo [6] Checking source syntax...
>>"run_log.txt" echo.
>>"run_log.txt" echo [6] Checking source syntax...
"%VPY%" -m py_compile app.py needs_engine.py config.py statistical_risk.py money_utils.py >>"run_log.txt" 2>&1
if errorlevel 1 (
  echo ERROR: Python syntax check failed.
  >>"run_log.txt" echo ERROR: Python syntax check failed.
  goto :END
)

echo.
echo [7] Starting Streamlit...
echo     http://127.0.0.1:8501
>>"run_log.txt" echo.
>>"run_log.txt" echo [7] Starting Streamlit at http://127.0.0.1:8501

"%VPY%" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false >>"run_log.txt" 2>&1

set "RC=%ERRORLEVEL%"
echo.
echo Streamlit exited with code %RC%.
>>"run_log.txt" echo Streamlit exited with code %RC%.

:END
echo.
echo Log file: %CD%\run_log.txt
>>"run_log.txt" echo.
>>"run_log.txt" echo ===== END =====
endlocal
