# Contributing to Claude Desktop MCP Manager

Thank you for your interest in contributing to the Claude Desktop MCP Manager! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Issues

If you encounter a bug or have a feature request:

1. **Check existing issues** first to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Detailed description of the problem or feature
   - Steps to reproduce (for bugs)
   - Your operating system and Python version
   - Screenshots if applicable

### Submitting Code Changes

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the coding standards below
4. **Test your changes** thoroughly
5. **Commit your changes** with clear, descriptive messages
6. **Push to your fork** and create a pull request

### Coding Standards

- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Add docstrings to new functions and classes
- **Comments**: Use clear, concise comments for complex logic
- **Error Handling**: Include proper exception handling
- **Cross-Platform**: Ensure code works on Windows, macOS, and Linux

### Code Organization

```
claude-desktop-mcp-manager/
├── mcp_manager.py          # Main application file
├── README.md               # Project documentation
├── LICENSE                 # MIT License
├── requirements.txt        # Python dependencies
├── setup.py               # Build configuration
├── build.sh               # Unix build script
├── build.bat              # Windows build script
└── .gitignore             # Git ignore rules
```

### Testing

Before submitting:

1. **Test on your platform** (Windows/macOS/Linux)
2. **Test with different config files** (existing, empty, missing)
3. **Test error conditions** (invalid paths, permissions, etc.)
4. **Test the GUI** (all buttons, dialogs, tabs)

### Feature Guidelines

When adding new features:

- **Maintain simplicity**: Keep the interface user-friendly
- **Cross-platform compatibility**: Ensure it works on all supported OS
- **Configuration safety**: Don't break existing configs
- **Backward compatibility**: Don't break existing functionality
- **Documentation**: Update README.md if needed

### UI/UX Guidelines

- **Consistent styling**: Use existing ttk widgets and styles
- **Clear labels**: Use descriptive text for buttons and fields
- **Error messages**: Provide helpful, actionable error messages
- **Responsive design**: Ensure proper window resizing behavior
- **Accessibility**: Consider keyboard navigation and screen readers

### Common Contribution Areas

We welcome contributions in these areas:

#### Bug Fixes
- Cross-platform compatibility issues
- Error handling improvements
- UI/UX bugs
- Configuration file handling

#### Features
- Additional MCP server templates
- Import/export functionality
- Server validation
- Theme support
- Localization

#### Documentation
- README improvements
- Code comments
- User guides
- Screenshots

#### Build System
- Automated builds
- Packaging improvements
- Distribution methods

### Attribution Requirements

When contributing, please note:

- All contributions will be under the MIT License
- Attribution to https://dawid.ai must be maintained
- Your contributions will be credited in the project

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-desktop-mcp-manager.git
   cd claude-desktop-mcp-manager
   ```

2. **Set up development environment**:
   ```bash
   # Create virtual environment (optional but recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install pyinstaller  # For building executables
   ```

3. **Run the application**:
   ```bash
   python mcp_manager.py
   ```

### Pull Request Process

1. **Ensure your PR**:
   - Has a clear title and description
   - References any related issues
   - Includes tests or testing instructions
   - Maintains code quality

2. **PR Review Process**:
   - Code will be reviewed for quality and compatibility
   - Changes may be requested
   - Once approved, it will be merged

3. **After Merge**:
   - Your contribution will be included in the next release
   - You'll be credited in the project

### Questions?

If you have questions about contributing:

- **Open an issue** for general questions
- **Check existing issues** for similar questions
- **Contact**: Visit https://dawid.ai for more information

### Code of Conduct

- Be respectful and constructive in all interactions
- Focus on what's best for the project and community
- Help maintain a welcoming environment for all contributors

Thank you for contributing to the Claude Desktop MCP Manager!