#!/bin/bash
# Build script for Claude Desktop MCP Manager

echo "Building Claude Desktop MCP Manager executables..."

# Create build directory
mkdir -p dist

# Build with PyInstaller (recommended)
if command -v pyinstaller &> /dev/null; then
    echo "Building with PyInstaller..."
    pyinstaller --onefile \
                --windowed \
                --name "Claude-MCP-Manager" \
                --distpath "./dist" \
                --workpath "./build" \
                --specpath "./build" \
                mcp_manager.py
    
    echo "PyInstaller build complete. Executable in ./dist/"
fi

# Alternative: Build with cx_Freeze
if command -v python setup.py &> /dev/null; then
    echo "Building with cx_Freeze as alternative..."
    python setup.py build
    echo "cx_Freeze build complete. Check ./build/ directory"
fi

echo "Build process finished!"
echo "Executables should be in ./dist/ or ./build/ directories"