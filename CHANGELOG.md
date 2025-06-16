# Changelog

All notable changes to Claude Desktop MCP Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Feature requests and improvements in development

### Changed
- Improvements and optimizations

### Fixed
- Bug fixes and stability improvements

## [1.0.0] - 2025-01-XX

### Added
- **Initial Release** 🎉
- Visual MCP server management interface
- Add, edit, remove, and pause/resume MCP servers
- Automatic configuration backup system
- Cross-platform support (Windows, macOS, Linux)
- Custom path configuration for Claude Desktop config and executable
- Settings persistence with user configuration file
- Debug console with real-time logging
- Claude Desktop restart integration
- Menu bar with File, Tools, and Help menus
- About dialog with attribution to https://dawid.ai
- Comprehensive error handling and user feedback

### Features
- **Server Management**:
  - Intuitive GUI for MCP server configuration
  - Support for command, arguments, and environment variables
  - Pause/resume functionality without losing configuration
  - Real-time server list updates

- **Configuration Safety**:
  - Automatic backups before any changes
  - JSON validation and error handling
  - Rollback capability through backup system

- **Cross-Platform Compatibility**:
  - Auto-detection of Claude Desktop config locations
  - Platform-specific executable path detection
  - Environment variable support (%APPDATA%, ~, etc.)

- **User Experience**:
  - Tabbed interface (Servers, Settings, Console)
  - Persistent user preferences
  - Comprehensive logging and debugging
  - Helpful error messages and guidance

- **Build System**:
  - PyInstaller and cx_Freeze support
  - Cross-platform build scripts
  - Standalone executable generation

### Technical Details
- **Language**: Python 3.7+
- **GUI Framework**: tkinter (standard library)
- **Dependencies**: Standard library only (no external dependencies)
- **License**: MIT License with attribution requirement
- **Configuration**: JSON-based with user-friendly editing

### Known Issues
- None reported in initial release

### Platform Support
- **Windows**: Tested on Windows 10/11
- **macOS**: Tested on macOS 12+
- **Linux**: Tested on Ubuntu 20.04+ and other major distributions

### Documentation
- Comprehensive README with installation and usage instructions
- Platform-specific configuration examples
- Build instructions for creating executables
- Contributing guidelines for developers

---

## Future Releases

### Planned Features
- **v1.1.0**:
  - Server templates for common MCP servers
  - Import/export configuration functionality
  - Enhanced error validation
  - UI themes support

- **v1.2.0**:
  - Localization support
  - Server health checking
  - Configuration wizards
  - Advanced logging options

- **v2.0.0**:
  - Plugin system
  - Remote configuration management
  - Enhanced UI with modern widgets
  - Integration with MCP registry

### Reporting Issues
If you encounter any issues or have feature requests, please:
1. Check existing issues on GitHub
2. Create a new issue with detailed information
3. Include your OS, Python version, and steps to reproduce

### Contributing
We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Note**: This changelog follows the [Keep a Changelog](https://keepachangelog.com/) format. Each release includes detailed information about additions, changes, deprecations, removals, fixes, and security updates.