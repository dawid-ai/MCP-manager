@echo off
REM Build script for Claude Desktop MCP Manager (Windows)

echo Building Claude Desktop MCP Manager executables...

REM Create build directory
if not exist dist mkdir dist

REM Build with PyInstaller (recommended)
where pyinstaller >nul 2>nul
if %errorlevel% == 0 (
    echo Building with PyInstaller...
    pyinstaller --onefile --windowed --name "Claude-MCP-Manager" --distpath "./dist" --workpath "./build" --specpath "./build" mcp_manager.py
    echo PyInstaller build complete. Executable in ./dist/
) else (
    echo PyInstaller not found. Install with: pip install pyinstaller
)

REM Alternative: Build with cx_Freeze
python --version >nul 2>nul
if %errorlevel% == 0 (
    echo Building with cx_Freeze as alternative...
    python setup.py build
    echo cx_Freeze build complete. Check ./build/ directory
)

echo Build process finished!
echo Executables should be in ./dist/ or ./build/ directories
pause