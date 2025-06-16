#!/usr/bin/env python3
"""
Setup script for building Claude Desktop MCP Manager executable
"""

from cx_Freeze import setup, Executable
import sys
import os

# Dependencies
build_exe_options = {
    "packages": ["tkinter", "json", "pathlib", "subprocess", "threading"],
    "excludes": ["test", "unittest"],
    "include_files": []
}

# Base for GUI applications (Windows)
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Executable configuration
executable = Executable(
    script="mcp_manager.py",
    base=base,
    target_name="Claude-MCP-Manager",
    icon=None  # Add icon file path here if you have one
)

setup(
    name="Claude Desktop MCP Manager",
    version="1.0.0",
    description="GUI tool for managing Claude Desktop MCP server configurations",
    author="Dawid",
    author_email="hello@dawid.ai",
    url="https://dawid.ai",
    options={"build_exe": build_exe_options},
    executables=[executable]
)