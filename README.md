# Claude Desktop MCP Manager

A comprehensive GUI tool for managing MCP (Model Context Protocol) servers in Claude Desktop's configuration file. Easily add, edit, pause, and remove MCP servers without manually editing JSON files.

## Features

- **Visual Server Management**: Add, edit, remove, and pause/resume MCP servers through an intuitive interface
- **Configuration Safety**: Automatic backups before any changes
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Custom Paths**: Configure custom locations for Claude Desktop config files and executables
- **Pause/Resume**: Temporarily disable servers without losing their configuration
- **Claude Desktop Integration**: Restart Claude Desktop directly from the tool
- **Debug Console**: Real-time logging and error tracking
- **Settings Management**: Persistent user preferences

## Why Use This Tool?

Managing MCP servers in Claude Desktop typically requires:
- Manually editing JSON configuration files
- Remembering complex file paths and syntax
- Risk of breaking the configuration with typos
- No easy way to temporarily disable servers
- Difficulty managing multiple server configurations

This tool solves all these problems with a user-friendly interface that handles the JSON manipulation behind the scenes.

## Installation

### Prerequisites

- Python 3.7 or higher
- tkinter (usually included with Python)

### Option 1: Direct Download

1. Download `mcp_manager.py` from this repository
2. Run directly with Python:
   ```bash
   python mcp_manager.py
   ```

### Option 2: Clone Repository


```bash
git clone https://github.com/YOUR_USERNAME/claude-desktop-mcp-manager.git
cd claude-desktop-mcp-manager
python mcp_manager.py
```

### Option 3: Executable

Pre-compiled executable for Windows: [Windows_v1.0.0.zip](Windows_v1.0.0.zip)



## Usage

### First Launch

1. **Run the application**: `python mcp_manager.py`
2. **Check the configuration path**: The tool auto-detects your Claude Desktop config location
3. **View existing servers**: Any current MCP servers will be displayed

### Adding a New Server

1. Click **"Add Server"**
2. Fill in the server details:
   - **Name**: Unique identifier for the server
   - **Command**: Executable command (e.g., `python`, `node`, `uvx`)
   - **Arguments**: Command-line arguments
   - **Environment Variables**: Key=value pairs (optional)
3. Click **"OK"** to add the server

### Managing Servers

- **Edit**: Select a server and click "Edit Server"
- **Remove**: Select a server and click "Remove Server" 
- **Pause/Resume**: Temporarily disable a server without deleting it
- **Save Config**: Write changes to Claude Desktop's config file
- **Restart Claude**: Restart Claude Desktop to apply changes

### Custom Configuration

Go to the **Settings** tab to:
- Set custom paths for Claude Desktop config files
- Configure Claude Desktop executable locations
- The tool supports environment variables like `%APPDATA%`, `~`, etc.

## Platform-Specific Information

### Windows

**Default Config Location:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Common Claude Executable Locations:**
```
%LOCALAPPDATA%\AnthropicClaude\Claude.exe
%LOCALAPPDATA%\Programs\Claude\Claude.exe
```

### macOS

**Default Config Location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Common Claude Executable Locations:**
```
/Applications/Claude.app
~/Applications/Claude.app
```

### Linux

**Default Config Location:**
```
~/.config/Claude/claude_desktop_config.json
```

**Common Claude Executable Locations:**
```
/usr/bin/claude
/usr/local/bin/claude
~/.local/bin/claude
/opt/Claude/claude
/snap/bin/claude
```

## Configuration File

The tool creates a user configuration file at `~/.mcp_manager_config.json` with your custom settings:

```json
{
  "claude_desktop_config_path": "",
  "claude_executable_paths": [],
  "comments": {
    "usage": "Set custom paths here or leave empty for auto-detection"
  }
}
```

## Example MCP Server Configurations

### SQLite MCP Server
- **Name**: `sqlite`
- **Command**: `uvx`
- **Arguments**: `mcp-server-sqlite --db-path /path/to/database.db`

### Filesystem MCP Server
- **Name**: `filesystem`
- **Command**: `npx`
- **Arguments**: `-y @modelcontextprotocol/server-filesystem /allowed/path`

### Custom Python Server
- **Name**: `my-server`
- **Command**: `python`
- **Arguments**: `-m my_mcp_server`
- **Environment**: `API_KEY=your_key_here`

## Troubleshooting

### Config File Not Found
- Check if Claude Desktop is installed
- Use the Settings tab to set a custom config path
- The tool will create a new config file if none exists

### Claude Desktop Won't Restart
- Verify Claude Desktop executable path in Settings
- Try manually restarting Claude Desktop
- Check the Console tab for error details

### Server Not Working
- Verify the command and arguments are correct
- Check environment variables
- Look at Claude Desktop's logs for MCP connection issues

## Building Executable

To create standalone executables:

### Using PyInstaller

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed --name "Claude-MCP-Manager" mcp_manager.py
```

### Using cx_Freeze

```bash
# Install cx_Freeze
pip install cx_freeze

# Build
python setup.py build
```

## Contributing

Contributions are welcome! Please feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Attribution

Created by [Dawid](https://dawid.ai)

When distributing or modifying this software, please maintain attribution to https://dawid.ai

## Support

- **Issues**: Open an issue on GitHub
- **Website**: https://dawid.ai
- **Documentation**: See this README and in-app help

## Changelog

### v1.0.0
- Initial release
- Basic MCP server management
- Cross-platform support
- Settings configuration
- Debug console

---

**Note**: This tool is not affiliated with Anthropic. It's a community tool to help manage Claude Desktop MCP configurations.