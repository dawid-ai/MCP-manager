# Claude Desktop MCP Manager - Project Structure

This document outlines the complete project structure for the Claude Desktop MCP Manager GitHub repository.

## Repository Structure

```
claude-desktop-mcp-manager/
├── .github/
│   └── workflows/
│       └── build.yml                 # GitHub Actions CI/CD
├── .gitignore                        # Git ignore rules
├── CHANGELOG.md                      # Version history and changes
├── CONTRIBUTING.md                   # Contribution guidelines
├── LICENSE                           # MIT License with attribution
├── PROJECT_STRUCTURE.md              # This file
├── README.md                         # Main project documentation
├── build.bat                         # Windows build script
├── build.sh                          # Unix/Linux build script
├── mcp_manager.py                    # Main application file
├── requirements.txt                  # Python dependencies
└── setup.py                          # Build configuration
```

## File Descriptions

### Core Application
- **`mcp_manager.py`** - Main application file containing all GUI and logic code
  - Single-file application for easy distribution
  - Uses only Python standard library (tkinter)
  - Cross-platform compatibility

### Documentation
- **`README.md`** - Comprehensive project documentation
  - Installation instructions for all platforms
  - Usage guide with examples
  - Troubleshooting section
  - Platform-specific information

- **`CONTRIBUTING.md`** - Guidelines for contributors
  - Code standards and practices
  - Development setup instructions
  - Pull request process

- **`CHANGELOG.md`** - Version history
  - Detailed release notes
  - Feature additions and bug fixes
  - Breaking changes documentation

- **`PROJECT_STRUCTURE.md`** - This file
  - Complete project organization
  - File descriptions and purposes

### Build System
- **`setup.py`** - cx_Freeze build configuration
  - Cross-platform executable generation
  - Dependency management
  - Metadata configuration

- **`build.sh`** - Unix/Linux build script
  - Automated PyInstaller builds
  - Alternative cx_Freeze option
  - Cross-platform executable creation

- **`build.bat`** - Windows build script
  - Same functionality as build.sh for Windows
  - Batch file for Windows environments

- **`requirements.txt`** - Python dependencies
  - Lists optional build dependencies
  - Documents standard library usage

### Configuration
- **`.gitignore`** - Git ignore patterns
  - Python build artifacts
  - IDE files
  - OS-specific files
  - Application-specific files

- **`LICENSE`** - MIT License
  - Open source license
  - Attribution requirement to https://dawid.ai
  - Usage and distribution rights

### CI/CD
- **`.github/workflows/build.yml`** - GitHub Actions
  - Automated builds on multiple platforms
  - Python version testing
  - Release automation
  - Artifact uploading

## Generated Files (Not in Repository)

These files are created during build or runtime:

### Build Artifacts
```
build/                                # Build temporary files
dist/                                 # Distribution executables
├── Claude-MCP-Manager.exe           # Windows executable
├── Claude-MCP-Manager               # Linux executable
└── Claude-MCP-Manager.app           # macOS application bundle
```

### User Data (Created at Runtime)
```
~/.mcp_manager_config.json           # User configuration
~/.mcp_manager_backups/              # Automatic backups
├── claude_desktop_config_backup_*.json
└── ...
```

## Development Workflow

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/claude-desktop-mcp-manager.git
cd claude-desktop-mcp-manager
```

### 2. Development
- Edit `mcp_manager.py` for code changes
- Update `README.md` for documentation changes
- Add entries to `CHANGELOG.md` for version tracking

### 3. Testing
```bash
# Test the application
python mcp_manager.py

# Test on different platforms
# Verify cross-platform compatibility
```

### 4. Building
```bash
# Unix/Linux
./build.sh

# Windows
build.bat

# Manual PyInstaller
pyinstaller --onefile --windowed --name "Claude-MCP-Manager" mcp_manager.py
```

### 5. Release Process
1. Update `CHANGELOG.md` with new version
2. Tag the release: `git tag v1.0.0`
3. Push tags: `git push --tags`
4. GitHub Actions will automatically build and create release

## Code Organization

### Main Application Structure
```python
# mcp_manager.py structure
class MCPManager:
    def __init__(self)              # Initialize application
    def create_widgets(self)        # Create GUI components
    def create_menu(self)           # Create menu bar
    def setup_main_tab(self)        # MCP servers tab
    def setup_settings_tab(self)    # Settings configuration
    def setup_console_tab(self)     # Debug console
    
    # Configuration management
    def load_config(self)           # Load Claude Desktop config
    def save_config(self)           # Save Claude Desktop config
    def load_user_config(self)      # Load user preferences
    def save_user_config(self)      # Save user preferences
    
    # Server management
    def add_server(self)            # Add new MCP server
    def edit_server(self)           # Edit existing server
    def remove_server(self)         # Remove server
    def toggle_pause(self)          # Pause/resume server
    
    # Utility functions
    def restart_claude(self)        # Restart Claude Desktop
    def backup_config(self)         # Create backup
    def log(self)                   # Debug logging

class ServerDialog:              # Server configuration dialog
    def __init__(self)           # Initialize dialog
    def ok_clicked(self)         # Handle OK button
    def cancel_clicked(self)     # Handle Cancel button
```

## Distribution Strategy

### Repository Distribution
- **GitHub Repository**: Source code and documentation
- **Releases**: Pre-built executables for all platforms
- **Tags**: Version management and release tracking

### Executable Distribution
- **Windows**: `.exe` files via GitHub Releases
- **macOS**: Application bundles via GitHub Releases
- **Linux**: Binary executables via GitHub Releases

### Source Distribution
- **Direct Download**: Single `mcp_manager.py` file
- **Git Clone**: Full repository with build system
- **Package Managers**: Future PyPI distribution

## Attribution Requirements

All distributions must maintain:
- Link to https://dawid.ai in About dialog
- Attribution in LICENSE file
- Reference in documentation
- Credit in derivative works

## Future Enhancements

### Project Structure Improvements
- Modular code organization
- Separate GUI and logic components
- Plugin system architecture
- Internationalization support

### Build System Enhancements
- Docker builds for consistent environments
- Automated testing integration
- Multiple distribution formats
- Dependency management improvements

---

This project structure ensures:
- Easy development and contribution
- Cross-platform compatibility
- Professional distribution
- Proper attribution maintenance
- Future scalability