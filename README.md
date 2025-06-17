# Claude Desktop MCP Manager

A comprehensive GUI tool for managing MCP (Model Context Protocol) servers in Claude Desktop's configuration file. Easily add, edit, pause, and remove MCP servers without manually editing JSON files.

## Features

- **Visual Server Management**: Add, edit, remove, and pause/resume MCP servers through an intuitive interface.
- **Configuration Safety**: Automatic backups before any changes are saved.
- **Cross-Platform**: Works on Windows, macOS, and Linux.
- **Custom Paths**: Configure custom locations for Claude Desktop config files and executables.
- **Pause/Resume**: Temporarily disable servers without losing their configuration.
- **Claude Desktop Integration**: Restart Claude Desktop directly from the tool.
- **Debug Console**: Real-time logging and error tracking.
- **Settings Management**: Persistent user preferences for paths.
- **Marketplace Tab**:
    - Discover and add pre-configured MCP servers from a curated list.
    - Search for servers by name or description.
    - View server details (description, instructions, owner, repository) before adding.
    - Manages its own database of marketplace servers, which can be updated from a remote source.
    - Displays local and remote database versions and allows users to update the local database.
- **Automatic Update Check**:
    - Checks for new application versions on startup.
    - Displays the current application version in the main tab.
    - If a new version is available, a button "Get Latest: vX.Y.Z" will appear, linking to the application's releases page.

## Why Use This Tool?

Managing MCP servers in Claude Desktop typically requires:
- Manually editing JSON configuration files.
- Remembering complex file paths and syntax.
- Risk of breaking the configuration with typos.
- No easy way to temporarily disable servers.
- Difficulty managing multiple server configurations.

This tool solves all these problems with a user-friendly interface that handles the JSON manipulation behind the scenes.

## Installation

### Prerequisites

- Python 3.7 or higher
- tkinter (usually included with Python)

### Option 1: Direct Download

1. Download `mcp_manager.py` from this repository.
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
*(Replace `YOUR_USERNAME` with the actual repository path if forking/cloning from a specific source).*

### Option 3: Executable

Pre-compiled executable for Windows: [Windows_v1.0.0.zip](Windows_v1.0.0.zip) *(Link may be outdated; check releases page for the latest version).*

## Usage

### First Launch

1. **Run the application**: `python mcp_manager.py`
2. **Check the configuration path**: The tool auto-detects your Claude Desktop config location. This is displayed on the "MCP Servers" tab.
3. **View existing servers**: Any current MCP servers will be displayed on the "MCP Servers" tab.
4. **Application Version**: The current version of MCP Manager is displayed on the "MCP Servers" tab. If an update is available, a button will guide you to the releases page.

### Managing Local MCP Servers (MCP Servers Tab)

- **Add Server**: Click "Add Server", fill in the details (Name, Command, Arguments, Environment Variables), and click "OK".
- **Edit Server**: Select a server from the list and click "Edit Server".
- **Remove Server**: Select a server and click "Remove Server".
- **Pause/Resume**: Select a server and click "Pause/Resume" to temporarily disable/enable it without deleting.
- **Save Config**: Click "Save Config" to write all active server configurations to your Claude Desktop `claude_desktop_config.json` file. This is necessary for Claude Desktop to use your changes.
- **Reload Config**: Click "Reload Config" to discard current changes in the tool and reload from the `claude_desktop_config.json` file.
- **Backup Config**: Manually trigger a backup of your current `claude_desktop_config.json`.
- **Restart Claude**: Click "Restart Claude Desktop" to attempt to close and reopen the Claude Desktop application.

### Marketplace Tab

- **Discover Servers**: Browse the list of available pre-configured MCP servers.
- **Search**: Use the search bar to filter servers by name or description.
- **View Details**: Click on a server in the list to see its full details (description, setup instructions, owner, repository link) in the panel below.
- **Update Database**:
    - The tab displays the version of your local marketplace database and checks for a remote version.
    - Click "Update Database" to download the latest list of marketplace servers.
- **Add to MCP Manager**:
    1. Select a server from the marketplace list.
    2. Review its details.
    3. Click "Add to MCP Manager".
    4. If a server with the same name already exists in your local MCP Servers list (on the first tab), you'll be asked to confirm overwriting.
    5. The server will be added to your local list on the "MCP Servers" tab. Remember to click "Save Config" on the "MCP Servers" tab to make it active in Claude Desktop.

### Custom Configuration (Settings Tab)

Go to the **Settings** tab to:
- Set a custom path for your Claude Desktop `claude_desktop_config.json` file if the auto-detected one is incorrect or you use a portable setup.
- Configure custom paths for the Claude Desktop executable if needed for the "Restart Claude Desktop" feature.
- The tool supports environment variables in paths (e.g., `%APPDATA%` on Windows, `~` for home directory on macOS/Linux).

## Platform-Specific Information

*(This section remains largely the same as provided previously, detailing default config locations and common Claude executable paths for Windows, macOS, and Linux.)*

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

The tool creates a user configuration file at `~/.mcp_manager_config.json` (Path is OS-dependent, typically in user's home/.config or AppData) for its own settings:

```json
{
  "claude_desktop_config_path": "", // Custom path to claude_desktop_config.json
  "claude_executable_paths": []     // Custom paths for Claude executable
}
```

## Example MCP Server Configurations

*(This section can remain as is, or be augmented with examples found in the marketplace if desired.)*

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

*(This section can be updated with potential issues related to the new features.)*

### Marketplace Issues
- **"Database not found. Please update."**: Click the "Update Database" button on the Marketplace tab. If issues persist, check your internet connection or the console for error messages.
- **"Could not retrieve full details..."**: The selected server might have an issue in the database, or the database schema might be outdated. Try updating the database.
- **JSON Parsing Errors when adding from Marketplace**: The `args` or `env_vars` field for a server in the marketplace database might be malformed. Contact the database maintainer or check the server's source repository.

### Config File Not Found
- Check if Claude Desktop is installed and has been run at least once.
- Use the Settings tab to set a custom config path if Claude Desktop's configuration is in a non-standard location.
- The tool will create a new config file if none exists when you save your MCP server configurations.

### Claude Desktop Won't Restart
- Verify the Claude Desktop executable path in the Settings tab.
- Try manually restarting Claude Desktop.
- Check the Console tab in MCP Manager for error details.

### Server Not Working in Claude Desktop
- Ensure you clicked "Save Config" in MCP Manager after adding/editing a server.
- Verify the command, arguments, and environment variables for the server are correct.
- Look at Claude Desktop's own logs for MCP connection issues or errors from the server itself.

## Marketplace Database Setup (For Maintainers)

To maintain the curated list of MCP servers for the Marketplace tab, you need to set up a SQLite database and a version file, typically hosted in a public GitHub repository.

### 1. Database File (`marketplace.db`)

This is a standard SQLite3 database file. It should contain two main tables:

#### `metadata` Table

Stores metadata about the database, primarily its version.

-   **Columns:**
    -   `key` (TEXT PRIMARY KEY): The name of the metadata key. Should include a row with `key = 'version'`.
    -   `value` (TEXT): The value for the key. For the 'version' key, this would be the database version string (e.g., `1.0.0`, `2023102701`).

#### `servers` Table

Stores the actual server configurations available in the marketplace.

-   **Columns:**
    -   `id` (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for each server entry.
    -   `name` (TEXT UNIQUE NOT NULL): The display name of the server (e.g., "My Custom Server"). This will be used as the default name when adding to MCP Manager.
    -   `description` (TEXT): A short, user-friendly description of what the server does or provides.
    -   `instructions` (TEXT): Detailed instructions on how to set up, use, or prerequisites for the server. Can include links or further notes.
    -   `owner_name` (TEXT): The name or handle of the server's creator or maintainer.
    -   `owner_link` (TEXT): A URL to the owner's GitHub profile, website, or contact page.
    -   `repo_link` (TEXT): A URL to the server's source code repository (if available).
    -   `command` (TEXT NOT NULL): The base command to execute the server (e.g., `python`, `node`, `my_server_executable`).
    -   `args` (TEXT): A JSON string representing a list of command-line arguments. Should default to an empty list string `[]` if not applicable.
        *   Example valid JSON: `["--port", "8080", "--verbose"]`
        *   Example for no arguments: `[]`
    -   `env_vars` (TEXT): A JSON string representing a dictionary of environment variables. Should default to an empty object string `{}` if not applicable.
        *   Example valid JSON: `{"API_KEY": "your_secret_value", "LOG_LEVEL": "info"}`
        *   Example for no environment variables: `{}`

### 2. Version File (e.g., `marketplace_version.txt`)

-   A plain text file.
-   Contains **only** the version string for the current `marketplace.db`.
-   This version string **must exactly match** the `value` associated with the `'version'` key in the `metadata` table of your `marketplace.db`.
-   Example content of `marketplace_version.txt`: `1.0.1`

### 3. Hosting

-   Place both `marketplace.db` and your version file (e.g., `marketplace_version.txt`) in a public GitHub repository.
-   The URLs required by the MCP Manager application are the **raw content URLs** for these files.
    -   Example for `marketplace_db_url`: `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/path/to/marketplace.db`
    -   Example for `marketplace_version_url`: `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/path/to/marketplace_version.txt`
-   These URLs need to be updated in the MCP Manager source code (specifically, `MCPManager.marketplace_db_url` and `MCPManager.marketplace_version_url` class attributes) if you are distributing your own build or maintaining a separate marketplace.

### 4. Updating the Marketplace

1.  Modify your local `marketplace.db` (add new servers, update existing ones, remove outdated ones). Ensure `args` and `env_vars` are stored as valid JSON strings.
2.  **Crucially, update the 'version' key in the `metadata` table within `marketplace.db` to a new version string.** This can be semantic (e.g., `1.0.1`) or date-based (e.g., `2023102801`).
3.  Update the content of your version file (e.g., `marketplace_version.txt`) to match this new version string.
4.  Commit and push both updated files (`marketplace.db` and the version file) to your GitHub repository.
5.  Users of MCP Manager will then see the new remote DB version and can use the "Update Database" button to download the latest `marketplace.db`.

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

# (setup.py might be needed for cx_Freeze)
# python setup.py build
```
*(Note: A `setup.py` file is typically required for cx_Freeze, which is not detailed here.)*

## Contributing

Contributions are welcome! Please feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (if available in the repository).

## Attribution

Created by [Dawid](https://dawid.ai)

When distributing or modifying this software, please maintain attribution to https://dawid.ai

## Support

- **Issues**: Open an issue on the GitHub repository.
- **Website**: https://dawid.ai
- **Documentation**: See this README and in-app help/tooltips.

## Changelog

### v1.0.0 (Assumed based on current implementation)
- Initial release with local MCP server management (Add, Edit, Remove, Pause/Resume).
- Settings for custom config and executable paths.
- Debug console.
- Marketplace tab for discovering and adding servers.
- Marketplace database update functionality.
- Application version check and update notification.

---

**Note**: This tool is not affiliated with Anthropic. It's a community tool to help manage Claude Desktop MCP configurations.