@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   InqBridge Setup
echo ============================================
echo.

:: --- Locate project root (where this script lives) ---
set "PROJECT_ROOT=%~dp0"
:: Remove trailing backslash
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

:: --- Check Python ---
echo [1/4] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on PATH.
    echo Install Python 3.12+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo   Found Python %PYVER%

:: --- Create venv if missing ---
echo.
echo [2/4] Setting up virtual environment...
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    echo   .venv already exists, skipping creation.
) else (
    echo   Creating .venv...
    python -m venv "%PROJECT_ROOT%\.venv"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
    echo   Created.
)

echo   Installing dependencies...
"%PROJECT_ROOT%\.venv\Scripts\pip.exe" install -q -e "%PROJECT_ROOT%[dev]"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)
echo   Dependencies installed.

:: --- Discover Inquisit installations ---
echo.
echo [3/4] Scanning for Inquisit installations...

set "FOUND_COUNT=0"
set "SEARCH_BASE=C:\Program Files\Millisecond Software"

if not exist "%SEARCH_BASE%" (
    echo   WARNING: %SEARCH_BASE% not found.
    echo   You can manually set the Inquisit path in local.json later.
    goto :write_local_no_inquisit
)

for /d %%D in ("%SEARCH_BASE%\Inquisit*") do (
    if exist "%%D\Inquisit.exe" (
        set /a FOUND_COUNT+=1
        set "INQUISIT_!FOUND_COUNT!=%%D\Inquisit.exe"
        set "INQUISIT_NAME_!FOUND_COUNT!=%%~nxD"
        echo   [!FOUND_COUNT!] %%~nxD  --  %%D\Inquisit.exe
    )
)

if %FOUND_COUNT%==0 (
    echo   No Inquisit installations found in %SEARCH_BASE%.
    echo   You can manually set the Inquisit path in local.json later.
    goto :write_local_no_inquisit
)

if %FOUND_COUNT%==1 (
    set "CHOSEN_EXE=!INQUISIT_1!"
    echo   Using: !INQUISIT_NAME_1!
    goto :write_local
)

:: Multiple versions found - ask user which one (license may differ per version)
echo.
echo   Multiple Inquisit versions found. Which one should InqBridge use?
echo   (Note: pick the version you have a license for)
set /p "CHOICE=  Enter number [1-%FOUND_COUNT%]: "

:: Validate choice
set "CHOSEN_EXE=!INQUISIT_%CHOICE%!"
if "!CHOSEN_EXE!"=="" (
    echo   Invalid choice. Defaulting to [1].
    set "CHOSEN_EXE=!INQUISIT_1!"
)
echo   Selected: !CHOSEN_EXE!
goto :write_local

:write_local_no_inquisit
set "CHOSEN_EXE="

:write_local
echo.
echo [4/4] Writing configuration files...

:: --- Write local.json ---
set "LOCAL_JSON=%PROJECT_ROOT%\local.json"
if "!CHOSEN_EXE!"=="" (
    (
        echo {
        echo   "inquisit_exe": null
        echo }
    ) > "%LOCAL_JSON%"
) else (
    :: Escape backslashes for JSON
    set "JSON_EXE=!CHOSEN_EXE:\=\\!"
    (
        echo {
        echo   "inquisit_exe": "!JSON_EXE!"
        echo }
    ) > "%LOCAL_JSON%"
)
echo   Wrote local.json

:: --- Write .mcp.json ---
set "MCP_JSON=%PROJECT_ROOT%\.mcp.json"
set "JSON_ROOT=%PROJECT_ROOT:\=\\%"
set "JSON_VENV=%PROJECT_ROOT:\=\\%\\.venv\\Scripts\\python.exe"
(
    echo {
    echo   "mcpServers": {
    echo     "inqbridge": {
    echo       "command": "!JSON_VENV!",
    echo       "args": ["-m", "mcp_server.main"],
    echo       "cwd": "!JSON_ROOT!"
    echo     }
    echo   }
    echo }
) > "%MCP_JSON%"
echo   Wrote .mcp.json

:: --- Write .claude/settings.local.json (enables MCP server in Claude Code) ---
if not exist "%PROJECT_ROOT%\.claude" mkdir "%PROJECT_ROOT%\.claude"
set "SETTINGS_JSON=%PROJECT_ROOT%\.claude\settings.local.json"
(
    echo {
    echo   "permissions": {},
    echo   "enableAllProjectMcpServers": true,
    echo   "enabledMcpjsonServers": ["inqbridge"]
    echo }
) > "%SETTINGS_JSON%"
echo   Wrote .claude/settings.local.json

echo.
echo ============================================
echo   Setup complete!
echo.
echo   Restart Claude Code to load the MCP server.
echo ============================================
endlocal
