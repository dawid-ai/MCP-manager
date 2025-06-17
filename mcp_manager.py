def ok_clicked(self):
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()
        args = self.args_var.get().strip()
        env_text = self.env_text.get('1.0', tk.END).strip()
        
        print(f"Dialog OK clicked - Name: '{name}', Command: '{command}', Args: '{args}', Env: '{env_text}'")
        
        if not name:
            messagebox.showerror("Error", "Server name is required")
            return
        
        if not command:
            messagebox.showerror("Error", "Command is required")
            return
        
        env = self.parse_env_vars(env_text) if env_text else {}
        
        print(f"Parsed environment variables: {env}")
        self.result = (name, command, args, env)
        print(f"Dialog result set to: {self.result}")
        self.dialog.destroy()#!/usr/bin/env python3
"""
Claude Desktop MCP Manager
A GUI tool for managing MCP (Model Context Protocol) servers in claude_desktop_config.json
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
import json
import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
import sys
import traceback
from datetime import datetime
import sqlite3
import urllib.request
import webbrowser

class MCPManager:
    APP_VERSION = "1.0.0"
    APP_LATEST_VERSION_URL = "YOUR_GITHUB_REPO_RAW_APP_VERSION_TXT_URL_HERE"  # Placeholder
    APP_RELEASES_PAGE_URL = "YOUR_GITHUB_REPO_RELEASES_PAGE_URL_HERE"    # Placeholder

    def __init__(self, root):
        self.root = root
        self.root.title(f"Claude Desktop MCP Manager {MCPManager.APP_VERSION}")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Load user configuration first
        self.user_config_path = Path.home() / ".mcp_manager_config.json"
        self.user_config = self.load_user_config()
        
        # Configuration
        self.config_path = self.get_config_path()
        self.backup_dir = Path.home() / ".mcp_manager_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Marketplace DB settings
        self.marketplace_db_path = Path.home() / ".mcp_manager_data" / "marketplace.db"
        self.marketplace_db_url = "YOUR_GITHUB_REPO_RAW_DB_URL_HERE"  # Placeholder
        self.marketplace_version_url = "YOUR_GITHUB_REPO_RAW_VERSION_TXT_URL_HERE"  # Placeholder
        self.marketplace_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.mcp_config = {}
        self.paused_servers = set()  # Servers that are paused (not in config but saved in our tool)
        self.selected_marketplace_server_details = None # For storing full details of selected marketplace server
        
        # Create GUI
        self.create_widgets()
        self.log(f"MCP Manager started")
        self.log(f"Config path: {self.config_path}")
        self.log(f"Config exists: {self.config_path.exists()}")
        self.load_config()
        self.refresh_server_list()
        self.check_db_version()
        self.load_marketplace_servers()
        self.check_app_version() # Check for app updates
        
    def load_user_config(self):
        """Load user configuration file with custom paths"""
        default_config = {
            "claude_desktop_config_path": "",  # Empty means use auto-detection
            "claude_executable_paths": [],     # Empty means use defaults
            "comments": {
                "claude_desktop_config_path_examples": {
                    "windows": [
                        "%APPDATA%\\Claude\\claude_desktop_config.json",
                        "C:\\Users\\USERNAME\\AppData\\Roaming\\Claude\\claude_desktop_config.json"
                    ],
                    "macos": [
                        "~/Library/Application Support/Claude/claude_desktop_config.json",
                        "/Users/USERNAME/Library/Application Support/Claude/claude_desktop_config.json"
                    ],
                    "linux": [
                        "~/.config/Claude/claude_desktop_config.json",
                        "/home/USERNAME/.config/Claude/claude_desktop_config.json"
                    ]
                },
                "claude_executable_paths_examples": {
                    "windows": [
                        "%LOCALAPPDATA%\\AnthropicClaude\\Claude.exe",
                        "%LOCALAPPDATA%\\Programs\\Claude\\Claude.exe",
                        "%PROGRAMFILES%\\Claude\\Claude.exe",
                        "C:\\Users\\USERNAME\\AppData\\Local\\AnthropicClaude\\Claude.exe"
                    ],
                    "macos": [
                        "/Applications/Claude.app",
                        "~/Applications/Claude.app",
                        "/Users/USERNAME/Applications/Claude.app"
                    ],
                    "linux": [
                        "/usr/bin/claude",
                        "/usr/local/bin/claude",
                        "~/.local/bin/claude",
                        "/opt/Claude/claude",
                        "/snap/bin/claude"
                    ]
                },
                "usage": "Set 'claude_desktop_config_path' to specify custom config file location. Set 'claude_executable_paths' to specify custom Claude executable locations (first found will be used). Use environment variables like %APPDATA%, %LOCALAPPDATA%, ~ etc."
            }
        }
        
        try:
            if self.user_config_path.exists():
                with open(self.user_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                # Create default config file
                self.save_user_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading user config: {e}")
            return default_config
    
    def save_user_config(self, config=None):
        """Save user configuration file"""
        try:
            config_to_save = config or self.user_config
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving user config: {e}")
            return False
        
    def get_config_path(self) -> Path:
        """Get the path to claude_desktop_config.json based on user config or OS detection"""
        # Check if user has specified a custom path
        custom_path = self.user_config.get('claude_desktop_config_path', '').strip()
        if custom_path:
            expanded_path = os.path.expandvars(os.path.expanduser(custom_path))
            return Path(expanded_path)
        
        # Fall back to OS-based detection
        system = platform.system()
        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif system == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        else:  # Linux/Unix
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    def create_widgets(self):
        # Create menu bar
        self.create_menu()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Main tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text='MCP Servers')
        
        # Settings tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text='Settings')
        
        # Console tab
        console_tab = ttk.Frame(notebook)
        notebook.add(console_tab, text='Console')

        # Marketplace tab
        marketplace_tab = ttk.Frame(notebook)
        notebook.add(marketplace_tab, text='Marketplace')
        
        # Setup tabs
        self.setup_main_tab(main_tab)
        self.setup_settings_tab(settings_tab)
        self.setup_console_tab(console_tab)
        self.setup_marketplace_tab(marketplace_tab)
    
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config...", command=self.browse_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_command(label="Backup Config", command=self.backup_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Restart Claude Desktop", command=self.restart_claude)
        tools_menu.add_command(label="Open Config Directory", command=self.open_config_directory)
        tools_menu.add_command(label="Open Backup Directory", command=self.open_backup_directory)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Visit dawid.ai", command=self.open_website)
    
    def open_config_directory(self):
        """Open the directory containing the config file"""
        try:
            config_dir = self.config_path.parent
            if config_dir.exists():
                import webbrowser
                webbrowser.open(str(config_dir))
            else:
                messagebox.showwarning("Warning", f"Config directory does not exist: {config_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open config directory: {str(e)}")
    
    def open_backup_directory(self):
        """Open the backup directory"""
        try:
            if self.backup_dir.exists():
                import webbrowser
                webbrowser.open(str(self.backup_dir))
            else:
                messagebox.showwarning("Warning", f"Backup directory does not exist: {self.backup_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open backup directory: {str(e)}")
    
    def open_website(self):
        """Open dawid.ai website"""
        try:
            import webbrowser
            webbrowser.open("https://dawid.ai")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open website: {str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""Claude Desktop MCP Manager {MCPManager.APP_VERSION}

A comprehensive GUI tool for managing MCP (Model Context Protocol) 
servers in Claude Desktop's configuration file.

Features:
• Visual server management
• Configuration safety with automatic backups
• Cross-platform support (Windows, macOS, Linux)
• Custom path configuration
• Pause/resume functionality
• Claude Desktop integration

Created by Dawid
Website: https://dawid.ai

This software is open source and distributed under the MIT License.
Attribution to https://dawid.ai must be maintained in distributions.

© 2025 - Licensed under MIT License"""
        
        # Create about dialog
        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About Claude Desktop MCP Manager")
        about_dialog.geometry("500x400")
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        
        # Center the dialog
        about_dialog.update_idletasks()
        x = (about_dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (about_dialog.winfo_screenheight() // 2) - (400 // 2)
        about_dialog.geometry(f"500x400+{x}+{y}")
        
        # Content frame
        content_frame = ttk.Frame(about_dialog, padding="20")
        content_frame.pack(fill='both', expand=True)
        
        # About text
        about_label = tk.Text(content_frame, wrap=tk.WORD, height=15, width=60)
        about_label.insert('1.0', about_text)
        about_label.config(state='disabled')  # Make read-only
        about_label.pack(fill='both', expand=True, pady=(0, 15))
        
        # Buttons frame
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x')
        
        ttk.Button(button_frame, text="Visit dawid.ai", command=self.open_website).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Close", command=about_dialog.destroy).pack(side=tk.RIGHT)

    def open_releases_page(self):
        self.log(f"Opening releases page: {MCPManager.APP_RELEASES_PAGE_URL}")
        try:
            webbrowser.open(MCPManager.APP_RELEASES_PAGE_URL, new=2) # new=2 opens in new tab if possible
        except Exception as e:
            self.log(f"Error opening releases page: {e}")
            messagebox.showerror("Error", f"Could not open releases page: {e}")

    def check_app_version(self):
        self.log("Checking for application updates...")
        if not hasattr(self, 'update_app_button'): # UI not ready
            self.log("Update_app_button not found, UI not fully ready for app version check.")
            return

        latest_version_str = None
        try:
            with urllib.request.urlopen(MCPManager.APP_LATEST_VERSION_URL, timeout=5) as response:
                latest_version_str = response.read().decode('utf-8').strip()

            self.log(f"Current app version: {MCPManager.APP_VERSION}, Fetched latest version: {latest_version_str}")

            # Simple version comparison (e.g., "v1.0.1" vs "v1.0.0")
            # Assumes "vX.Y.Z" format. More robust parsing might be needed for complex scenarios.
            current_v_parts = tuple(map(int, MCPManager.APP_VERSION.lstrip('v').split('.')))
            latest_v_parts = tuple(map(int, latest_version_str.lstrip('v').split('.')))

            if latest_v_parts > current_v_parts:
                self.log(f"Newer version available: {latest_version_str}")
                self.update_app_button.config(text=f"Update to {latest_version_str}!", style="Accent.TButton")
                # self.update_app_button.pack() # Or ensure it's visible if previously hidden
            else:
                self.log("Application is up-to-date.")
                self.update_app_button.config(text="Up to Date", state=tk.DISABLED)

        except urllib.error.URLError as e:
            self.log(f"Could not fetch latest app version (URLError): {e.reason}")
            self.update_app_button.config(text="Update Check Failed", state=tk.DISABLED)
        except Exception as e:
            self.log(f"Error checking app version: {e}")
            self.update_app_button.config(text="Update Check Error", state=tk.DISABLED)

    def setup_console_tab(self, console_tab):
        """Setup the console tab for debugging"""
        console_frame = ttk.Frame(console_tab, padding="10")
        console_frame.pack(fill='both', expand=True)
        
        # Console output
        self.console_text = scrolledtext.ScrolledText(console_frame, height=30, width=100)
        self.console_text.pack(fill='both', expand=True)
        
        # Buttons
        button_frame = ttk.Frame(console_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(button_frame, text="Clear Console", command=self.clear_console).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Save Log", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))

    def setup_marketplace_tab(self, tab_frame):
        """Setup the marketplace tab"""
        # Clear placeholder content if any (e.g. from previous version)
        for widget in tab_frame.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(tab_frame, padding="10")
        main_frame.pack(fill='both', expand=True)

        # Top Section (Info & Controls)
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))

        self.local_db_version_label = ttk.Label(top_frame, text="Local DB: N/A")
        self.local_db_version_label.pack(side=tk.LEFT, padx=(0, 10))

        self.remote_db_version_label = ttk.Label(top_frame, text="Remote DB: N/A")
        self.remote_db_version_label.pack(side=tk.LEFT, padx=(0, 20))

        self.update_db_button = ttk.Button(top_frame, text="Update Database", command=self.update_local_db)
        self.update_db_button.pack(side=tk.LEFT, padx=(0, 10))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_button = ttk.Button(top_frame, text="Search", command=lambda: self.load_marketplace_servers(self.search_var.get()))
        search_button.pack(side=tk.LEFT)

        # Middle Section (Server List)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True, pady=(0,10))

        columns = ('Name', 'Description', 'Owner')
        self.marketplace_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')

        self.marketplace_tree.heading('Name', text='Name')
        self.marketplace_tree.column('Name', width=150, minwidth=100)
        self.marketplace_tree.heading('Description', text='Description')
        self.marketplace_tree.column('Description', width=300, minwidth=200)
        self.marketplace_tree.heading('Owner', text='Owner')
        self.marketplace_tree.column('Owner', width=100, minwidth=80)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.marketplace_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.marketplace_tree.xview)
        self.marketplace_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.marketplace_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.marketplace_tree.bind('<<TreeviewSelect>>', self.on_marketplace_server_select)

        # Bottom Section (Details & Add Button)
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill='x')

        self.server_details_text = scrolledtext.ScrolledText(bottom_frame, height=6, wrap=tk.WORD, state='disabled')
        self.server_details_text.pack(fill='x', expand=True, side=tk.LEFT, padx=(0,10))

        self.add_from_marketplace_button = ttk.Button(bottom_frame, text="Add to MCP Manager", command=self.add_server_from_marketplace)
        self.add_from_marketplace_button.pack(side=tk.RIGHT, anchor='center', pady=(5,0))

    def on_marketplace_server_select(self, event):
        self.server_details_text.config(state='normal')
        self.server_details_text.delete('1.0', tk.END)
        self.selected_marketplace_server_details = None

        selection = self.marketplace_tree.selection()
        if not selection:
            self.server_details_text.config(state='disabled')
            return

        item = self.marketplace_tree.item(selection[0])
        server_name_in_tree = item['values'][0] # Name is the first column

        # Check for placeholder messages in the tree
        placeholder_messages = ["Database not found. Please update.", "No servers found.", "Error loading servers:", "Unexpected error:"]
        if any(server_name_in_tree.startswith(msg_start) for msg_start in placeholder_messages):
            self.log(f"Selected item is a placeholder/error message: '{server_name_in_tree}'")
            self.server_details_text.insert('1.0', server_name_in_tree) # Display the placeholder message itself
            self.server_details_text.config(state='disabled')
            return

        self.log(f"Fetching details for marketplace server: {server_name_in_tree}")

        if not self.marketplace_db_path.exists():
            self.log("Marketplace database file not found for detail view.")
            self.server_details_text.insert('1.0', "Database not found. Cannot fetch details.")
            self.server_details_text.config(state='disabled')
            return

        details_row = None
        conn = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()
            # Assuming 'servers' table and these columns exist. Adjust as per actual schema.
            query = """SELECT name, description, instructions, owner_name, owner_link,
                              repo_link, command, args, env_vars
                       FROM servers WHERE name = ?"""
            cursor.execute(query, (server_name_in_tree,))
            details_row = cursor.fetchone()

            if details_row:
                column_names = [col[0] for col in cursor.description]
                self.selected_marketplace_server_details = dict(zip(column_names, details_row))
                self.log(f"Fetched details: {self.selected_marketplace_server_details}")

                display_text = f"Name: {self.selected_marketplace_server_details.get('name', 'N/A')}\n"
                display_text += f"Description: {self.selected_marketplace_server_details.get('description', 'N/A')}\n\n"
                display_text += f"Instructions:\n{self.selected_marketplace_server_details.get('instructions', 'N/A')}\n\n"
                display_text += f"Owner: {self.selected_marketplace_server_details.get('owner_name', 'N/A')}"
                if self.selected_marketplace_server_details.get('owner_link'):
                    display_text += f" ({self.selected_marketplace_server_details.get('owner_link')})\n"
                else:
                    display_text += "\n"
                display_text += f"Repository: {self.selected_marketplace_server_details.get('repo_link', 'N/A')}\n"
                # Optionally, display command, args, env_vars or keep for add_server functionality
                # display_text += f"\nCommand: {self.selected_marketplace_server_details.get('command', 'N/A')}\n"
                # display_text += f"Args: {self.selected_marketplace_server_details.get('args', 'N/A')}\n"
                # display_text += f"Env Vars: {self.selected_marketplace_server_details.get('env_vars', 'N/A')}\n"
                self.server_details_text.insert('1.0', display_text)
            else:
                self.log(f"No details found in DB for server: {server_name_in_tree}")
                self.server_details_text.insert('1.0', "Could not retrieve full details for the selected server.")

        except sqlite3.Error as e:
            self.log(f"SQLite error while fetching details for {server_name_in_tree}: {e}")
            self.server_details_text.insert('1.0', f"Database error fetching details: {e}")
        except Exception as e:
            self.log(f"Unexpected error fetching details for {server_name_in_tree}: {e}")
            self.server_details_text.insert('1.0', f"Unexpected error: {e}")
        finally:
            if conn:
                conn.close()
            self.server_details_text.config(state='disabled')

    def download_db(self, url):
        self.log(f"Attempting to download DB from {url} to {self.marketplace_db_path}")
        try:
            with urllib.request.urlopen(url) as response, open(self.marketplace_db_path, 'wb') as out_file:
                data = response.read() # a `bytes` object
                out_file.write(data)
            self.log("Database downloaded successfully.")
            return True
        except urllib.error.URLError as e:
            self.log(f"Error downloading database (URL Error): {e.reason}")
            messagebox.showerror("Download Error", f"Failed to download database: {e.reason}")
        except IOError as e:
            self.log(f"Error saving database (IO Error): {e}")
            messagebox.showerror("Download Error", f"Failed to save database: {e}")
        except Exception as e:
            self.log(f"An unexpected error occurred during database download: {e}")
            messagebox.showerror("Download Error", f"An unexpected error occurred: {e}")
        return False

    def check_db_version(self):
        self.log("Checking DB versions...")
        remote_version_string = "Error"
        try:
            self.log(f"Fetching remote version from: {self.marketplace_version_url}")
            with urllib.request.urlopen(self.marketplace_version_url, timeout=5) as response:
                # Read and decode. Assume version is plain text, remove any leading/trailing whitespace
                remote_version_string = response.read().decode('utf-8').strip()
            self.log(f"Successfully fetched remote version: {remote_version_string}")
        except urllib.error.URLError as e:
            self.log(f"Error fetching remote version (URLError): {e.reason}")
            remote_version_string = "N/A (Connection)"
        except Exception as e:
            self.log(f"Unexpected error fetching remote version: {e}")
            remote_version_string = "N/A (Error)"

        if hasattr(self, 'remote_db_version_label'): # Ensure GUI is initialized
            self.remote_db_version_label.config(text=f"Remote DB: {remote_version_string}")

        local_version_string = "N/A"
        self.log(f"Checking local DB at: {self.marketplace_db_path}")
        if self.marketplace_db_path.exists():
            conn = None
            try:
                conn = sqlite3.connect(self.marketplace_db_path)
                cursor = conn.cursor()
                # Ensure the table and query are correct.
                # This assumes a 'metadata' table with 'key' and 'value' columns.
                cursor.execute("SELECT value FROM metadata WHERE key = 'version'")
                row = cursor.fetchone()
                if row:
                    local_version_string = row[0]
                    self.log(f"Found local DB version: {local_version_string}")
                else:
                    local_version_string = "Unknown (no version)"
                    self.log("Local DB version key not found in metadata.")
            except sqlite3.Error as e:
                # This can happen if the DB is not initialized, table doesn't exist, etc.
                self.log(f"SQLite error while reading local DB version: {e}")
                local_version_string = "Unknown (DB error)"
            except Exception as e:
                self.log(f"Unexpected error reading local DB version: {e}")
                local_version_string = "Error"
            finally:
                if conn:
                    conn.close()
        else:
            local_version_string = "Not found"
            self.log("Local DB file does not exist.")

        if hasattr(self, 'local_db_version_label'): # Ensure GUI is initialized
            self.local_db_version_label.config(text=f"Local DB: {local_version_string}")

        self.log(f"DB Versions - Local: {local_version_string}, Remote: {remote_version_string}")

    def update_local_db(self):
        self.log("Starting local marketplace database update process...")
        # Consider disabling update_db_button here if it's a long process
        # self.update_db_button.config(state=tk.DISABLED)

        download_success = self.download_db(self.marketplace_db_url)

        if download_success:
            self.log("Database download successful. Refreshing versions and server list.")
            self.check_db_version()  # Refresh local and remote version labels
            self.load_marketplace_servers()  # Refresh the treeview
            messagebox.showinfo("Success", "Marketplace database updated successfully.")
            self.log("Marketplace database update process completed successfully.")
        else:
            self.log("Database download failed.")
            messagebox.showerror("Error", "Failed to update marketplace database. Check logs for details.")
            self.log("Marketplace database update process failed.")

        # Re-enable button if it was disabled
        # if hasattr(self, 'update_db_button'):
        #     self.update_db_button.config(state=tk.NORMAL)

    def load_marketplace_servers(self, search_term=None):
        self.log(f"Loading marketplace servers. Search term: '{search_term if search_term else ''}'")

        # Clear existing treeview items
        for item in self.marketplace_tree.get_children():
            self.marketplace_tree.delete(item)

        if not self.marketplace_db_path.exists():
            self.log("Marketplace database file not found.")
            self.marketplace_tree.insert('', 'end', values=("Database not found. Please update.", "", ""))
            return

        servers_data = []
        conn = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()

            query_params = []
            sql_query = "SELECT name, description, owner_name FROM servers" # Ensure 'owner_name' is the correct column name

            if search_term:
                sql_query += " WHERE name LIKE ? OR description LIKE ?"
                # Potentially add more fields to search, e.g. owner_name:
                # sql_query += " OR owner_name LIKE ?"
                # query_params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
                query_params.extend([f"%{search_term}%", f"%{search_term}%"])

            self.log(f"Executing SQL: {sql_query} with params: {query_params}")
            cursor.execute(sql_query, query_params)
            servers_data = cursor.fetchall()

        except sqlite3.Error as e:
            self.log(f"Error loading marketplace servers: {e}")
            self.marketplace_tree.insert('', 'end', values=(f"Error loading servers: {e}", "", ""))
            return # Return early on error
        except Exception as e: # Catch any other unexpected errors
            self.log(f"Unexpected error loading marketplace servers: {e}")
            self.marketplace_tree.insert('', 'end', values=(f"Unexpected error: {e}", "", ""))
            return
        finally:
            if conn:
                conn.close()

        if servers_data:
            for server_row in servers_data:
                self.marketplace_tree.insert('', 'end', values=server_row)
            self.log(f"Loaded {len(servers_data)} servers into the marketplace tree.")
        else:
            self.log("No servers found matching the criteria.")
            self.marketplace_tree.insert('', 'end', values=("No servers found.", "", ""))

    def add_server_from_marketplace(self):
        self.log("Attempting to add server from marketplace...")

        if not self.selected_marketplace_server_details:
            messagebox.showwarning("No Server Selected", "Please select a server from the marketplace list first and ensure its details are loaded.")
            self.log("Add server from marketplace failed: No server details selected.")
            return

        details = self.selected_marketplace_server_details
        name = details.get('name')
        command = details.get('command')
        args_str = details.get('args', '[]') # Default to JSON string for an empty list
        env_str = details.get('env_vars', '{}') # Default to JSON string for an empty dict

        if not name or not command:
            messagebox.showerror("Configuration Error", "Selected server has incomplete configuration (missing name or command). Cannot add.")
            self.log(f"Add server from marketplace failed: Missing name or command for server '{name}'.")
            return

        try:
            args = json.loads(args_str)
            if not isinstance(args, list):
                self.log(f"Parsed 'args' for server '{name}' is not a list: {args}. Defaulting to empty list.")
                args = []
        except json.JSONDecodeError as e:
            messagebox.showerror("Configuration Error", f"Could not parse 'args' for '{name}': {e}. Please ensure it's a valid JSON list (e.g., [\"arg1\", \"arg2\"]).")
            self.log(f"Add server from marketplace failed: JSONDecodeError for args of server '{name}': {e}")
            return

        try:
            env = json.loads(env_str)
            if not isinstance(env, dict):
                self.log(f"Parsed 'env_vars' for server '{name}' is not a dictionary: {env}. Defaulting to empty dict.")
                env = {}
        except json.JSONDecodeError as e:
            messagebox.showerror("Configuration Error", f"Could not parse 'env_vars' for '{name}': {e}. Please ensure it's a valid JSON object (e.g., {{\"KEY\": \"value\"}}).")
            self.log(f"Add server from marketplace failed: JSONDecodeError for env_vars of server '{name}': {e}")
            return

        if name in self.mcp_config:
            if not messagebox.askyesno("Confirm Overwrite", f"Server '{name}' already exists in your MCP Servers. Overwrite it?"):
                self.log(f"User cancelled overwriting existing server '{name}'.")
                return
            self.log(f"User confirmed overwriting existing server '{name}'.")

        server_config = {'command': command}
        if args: # Only add 'args' key if args list is not empty
            server_config['args'] = args
        if env:  # Only add 'env' key if env dict is not empty
            server_config['env'] = env

        self.mcp_config[name] = server_config
        self.paused_servers.discard(name)  # Ensure the server is active

        self.refresh_server_list()  # Update the tree in the main "MCP Servers" tab
        messagebox.showinfo("Success", f"Server '{name}' added/updated in MCP Manager.")
        self.log(f"Server '{name}' successfully added/updated from marketplace with config: {server_config}")

    # open_releases_page and check_app_version are moved above create_widgets

    def setup_settings_tab(self, settings_tab):
        """Setup the settings tab for path configuration"""
        settings_frame = ttk.Frame(settings_tab, padding="20")
        settings_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(settings_frame, text="MCP Manager Settings", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Config file path section
        config_section = ttk.LabelFrame(settings_frame, text="Claude Desktop Config File", padding="10")
        config_section.pack(fill='x', pady=(0, 15))
        
        # Current path
        current_frame = ttk.Frame(config_section)
        current_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(current_frame, text="Current Path:").pack(anchor='w')
        current_path_label = ttk.Label(current_frame, text=str(self.config_path), 
                                     font=('Courier', 9), foreground='blue')
        current_path_label.pack(anchor='w', pady=(2, 0))
        
        # Custom path entry
        custom_frame = ttk.Frame(config_section)
        custom_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(custom_frame, text="Custom Path (leave empty for auto-detection):").pack(anchor='w')
        self.custom_config_var = tk.StringVar(value=self.user_config.get('claude_desktop_config_path', ''))
        custom_config_entry = ttk.Entry(custom_frame, textvariable=self.custom_config_var, width=80)
        custom_config_entry.pack(fill='x', pady=(2, 0))
        
        # Browse button
        ttk.Button(custom_frame, text="Browse", command=self.browse_custom_config).pack(pady=(5, 0))
        
        # Claude executable section
        exe_section = ttk.LabelFrame(settings_frame, text="Claude Desktop Executable", padding="10")
        exe_section.pack(fill='both', expand=True, pady=(0, 15))
        
        # Current executable paths
        ttk.Label(exe_section, text="Custom Executable Paths (one per line, first found will be used):").pack(anchor='w')
        
        # Text area for executable paths
        exe_frame = ttk.Frame(exe_section)
        exe_frame.pack(fill='both', expand=True, pady=(5, 10))
        
        self.exe_paths_text = scrolledtext.ScrolledText(exe_frame, height=8, width=80)
        self.exe_paths_text.pack(fill='both', expand=True)
        
        # Populate current executable paths
        current_paths = self.user_config.get('claude_executable_paths', [])
        if current_paths:
            self.exe_paths_text.insert('1.0', '\n'.join(current_paths))
        
        # Help text
        help_text = """Path Examples by OS:
Windows: %LOCALAPPDATA%\\AnthropicClaude\\Claude.exe, %LOCALAPPDATA%\\Programs\\Claude\\Claude.exe
macOS: /Applications/Claude.app, ~/Applications/Claude.app
Linux: /usr/bin/claude, ~/.local/bin/claude, /opt/Claude/claude

Environment variables like %APPDATA%, %LOCALAPPDATA%, ~ are supported."""
        
        help_label = ttk.Label(exe_section, text=help_text, font=('Arial', 8), 
                              foreground='gray', justify='left')
        help_label.pack(anchor='w', pady=(5, 0))
        
        # Save settings button
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(save_frame, text="Save Settings", command=self.save_settings).pack()
        ttk.Button(save_frame, text="Reset to Defaults", command=self.reset_settings).pack(pady=(5, 0))
    
    def browse_custom_config(self):
        """Browse for custom config file"""
        filename = filedialog.askopenfilename(
            title="Select claude_desktop_config.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(self.config_path.parent) if self.config_path.exists() else str(Path.home())
        )
        if filename:
            self.custom_config_var.set(filename)
    
    def save_settings(self):
        """Save user settings"""
        try:
            # Update user config
            self.user_config['claude_desktop_config_path'] = self.custom_config_var.get().strip()
            
            # Get executable paths from text widget
            exe_paths_text = self.exe_paths_text.get('1.0', tk.END).strip()
            exe_paths = [path.strip() for path in exe_paths_text.split('\n') if path.strip()]
            self.user_config['claude_executable_paths'] = exe_paths
            
            # Save to file
            if self.save_user_config():
                # Update current config path
                old_path = self.config_path
                self.config_path = self.get_config_path()
                
                self.log(f"Settings saved. Config path changed from {old_path} to {self.config_path}")
                
                # Reload config if path changed
                if old_path != self.config_path:
                    self.config_path_var.set(str(self.config_path))
                    self.load_config()
                    self.refresh_server_list()
                
                messagebox.showinfo("Success", "Settings saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save settings")
                
        except Exception as e:
            self.log(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            try:
                # Reset to defaults
                self.user_config = self.load_user_config()  # This will create defaults
                self.custom_config_var.set('')
                self.exe_paths_text.delete('1.0', tk.END)
                
                # Update config path
                self.config_path = self.get_config_path()
                self.config_path_var.set(str(self.config_path))
                
                self.log("Settings reset to defaults")
                messagebox.showinfo("Success", "Settings reset to defaults!")
                
            except Exception as e:
                self.log(f"Error resetting settings: {e}")
                messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")
    def setup_main_tab(self, main_frame):
        """Setup the main MCP servers tab"""
        main_frame = ttk.Frame(main_frame, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Claude Desktop MCP Server Manager", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Config path info
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        ttk.Label(config_frame, text="Config File:").grid(row=0, column=0, sticky=tk.W, pady=(0,2))
        self.config_path_var = tk.StringVar(value=str(self.config_path))
        config_entry = ttk.Entry(config_frame, textvariable=self.config_path_var, state='readonly')
        config_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0,2))
        
        ttk.Button(config_frame, text="Browse", command=self.browse_config).grid(row=0, column=2, padx=(5, 0), pady=(0,2))
        
        # App Version and Update button
        app_info_frame = ttk.Frame(config_frame)
        app_info_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5,0))

        self.current_app_version_label = ttk.Label(app_info_frame, text=f"Version: {MCPManager.APP_VERSION}")
        self.current_app_version_label.pack(side=tk.LEFT, padx=(0,10))

        self.update_app_button = ttk.Button(app_info_frame, text="Check for Updates", command=self.open_releases_page)
        self.update_app_button.pack(side=tk.LEFT)
        # The button's text/state will be updated by check_app_version
        # Initially, we can hide it or set to a default state if preferred:
        # self.update_app_button.pack_forget()


        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(config_frame, textvariable=self.status_var, foreground="green")
        status_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0)) # Adjusted row
        
        # Server list frame
        list_frame = ttk.LabelFrame(main_frame, text="MCP Servers", padding="5")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for servers
        columns = ('Name', 'Command', 'Args', 'Status')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)
        
        # Configure columns
        self.tree.heading('#0', text='')
        self.tree.column('#0', width=0, stretch=False)
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == 'Name':
                self.tree.column(col, width=150, minwidth=100)
            elif col == 'Status':
                self.tree.column(col, width=80, minwidth=80)
            elif col == 'Command':
                self.tree.column(col, width=200, minwidth=150)
            else:
                self.tree.column(col, width=250, minwidth=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        # Server management buttons
        ttk.Button(button_frame, text="Add Server", command=self.add_server).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit Server", command=self.edit_server).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove Server", command=self.remove_server).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Pause/Resume", command=self.toggle_pause).pack(side=tk.LEFT, padx=(0, 15))
        
        # Config management buttons
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Reload Config", command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Backup Config", command=self.backup_config).pack(side=tk.LEFT, padx=(0, 15))
        
        # Claude Desktop control
        ttk.Button(button_frame, text="Restart Claude Desktop", command=self.restart_claude, 
                  style='Accent.TButton').pack(side=tk.RIGHT)
    
    def log(self, message):
        """Add message to console log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        if hasattr(self, 'console_text'):
            self.console_text.insert(tk.END, log_message)
            self.console_text.see(tk.END)
        print(log_message.strip())  # Also print to stdout
    
    def clear_console(self):
        """Clear the console output"""
        if hasattr(self, 'console_text'):
            self.console_text.delete(1.0, tk.END)
    
    def save_log(self):
        """Save console log to file"""
        try:
            if hasattr(self, 'console_text'):
                log_content = self.console_text.get(1.0, tk.END)
                filename = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    title="Save Console Log"
                )
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(log_content)
                    messagebox.showinfo("Success", f"Log saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log: {str(e)}")
    
    def browse_config(self):
        """Browse for configuration file"""
        filename = filedialog.askopenfilename(
            title="Select claude_desktop_config.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(self.config_path.parent)
        )
        if filename:
            self.config_path = Path(filename)
            self.config_path_var.set(str(self.config_path))
            self.load_config()
            self.refresh_server_list()
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            self.log(f"Loading config from: {self.config_path}")
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.mcp_config = config.get('mcpServers', {})
                self.log(f"Loaded {len(self.mcp_config)} servers from config")
                self.log(f"Server names: {list(self.mcp_config.keys())}")
                self.status_var.set(f"Loaded {len(self.mcp_config)} servers from config")
            else:
                self.mcp_config = {}
                self.log("Config file not found - will create new one")
                self.status_var.set("Config file not found - will create new one")
        except Exception as e:
            error_msg = f"Failed to load config: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            messagebox.showerror("Error", f"Failed to load config: {str(e)}")
            self.status_var.set("Error loading config")
    
    def save_config(self):
        """Save configuration to JSON file"""
        try:
            # Create backup first
            if self.config_path.exists():
                backup_path = self.backup_dir / f"claude_desktop_config_backup_{int(os.path.getmtime(self.config_path))}.json"
                shutil.copy2(self.config_path, backup_path)
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing config or create new one
            config = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except:
                    pass
            
            # Update MCP servers
            config['mcpServers'] = self.mcp_config
            
            # Save config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.status_var.set("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
            self.status_var.set("Error saving config")
    
    def backup_config(self):
        """Create a backup of the current configuration"""
        try:
            if not self.config_path.exists():
                messagebox.showwarning("Warning", "No config file to backup")
                return
            
            timestamp = int(os.path.getmtime(self.config_path))
            backup_path = self.backup_dir / f"claude_desktop_config_backup_{timestamp}.json"
            shutil.copy2(self.config_path, backup_path)
            messagebox.showinfo("Success", f"Backup created: {backup_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create backup: {str(e)}")
    
    def refresh_server_list(self):
        """Refresh the server list display"""
        self.log("Refreshing server list...")
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add active servers
        for name, config in self.mcp_config.items():
            command = config.get('command', '')
            args = ' '.join(config.get('args', []))
            status = 'Paused' if name in self.paused_servers else 'Active'
            
            self.log(f"Adding server: {name} - {command} - Status: {status}")
            self.tree.insert('', 'end', values=(name, command, args, status))
        
        # Add paused servers that aren't in config
        for name in self.paused_servers:
            if name not in self.mcp_config:
                self.log(f"Adding paused server: {name}")
                self.tree.insert('', 'end', values=(name, '(Paused)', '', 'Paused'))
        
        self.log(f"Server list refreshed. Total items: {len(self.tree.get_children())}")
    
    def add_server(self):
        """Add a new MCP server"""
        self.log("Opening add server dialog...")
        dialog = ServerDialog(self.root, "Add MCP Server")
        
        # Wait for dialog to complete
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            name, command, args, env = dialog.result
            self.log(f"Adding server: {name}, command: {command}, args: {args}, env: {env}")
            
            if name in self.mcp_config:
                if not messagebox.askyesno("Confirm", f"Server '{name}' already exists. Replace it?"):
                    self.log(f"User cancelled replacing existing server: {name}")
                    return
            
            server_config = {'command': command}
            if args:
                server_config['args'] = args.split() if isinstance(args, str) else args
            if env:
                server_config['env'] = env
            
            self.mcp_config[name] = server_config
            self.paused_servers.discard(name)  # Remove from paused if it was there
            
            self.log(f"Server added to config: {name} -> {server_config}")
            self.log(f"Current mcp_config: {self.mcp_config}")
            
            self.refresh_server_list()
            self.status_var.set(f"Added server: {name}")
        else:
            self.log("Add server dialog was cancelled or had no result")
    
    def edit_server(self):
        """Edit selected MCP server"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a server to edit")
            return
        
        item = self.tree.item(selection[0])
        name = item['values'][0]
        
        if name in self.mcp_config:
            config = self.mcp_config[name]
            command = config.get('command', '')
            args = ' '.join(config.get('args', []))
            env = config.get('env', {})
        else:
            command = args = ''
            env = {}
        
        dialog = ServerDialog(self.root, "Edit MCP Server", name, command, args, env)
        if dialog.result:
            new_name, new_command, new_args, new_env = dialog.result
            
            # Remove old entry if name changed
            if new_name != name and name in self.mcp_config:
                del self.mcp_config[name]
                self.paused_servers.discard(name)
            
            # Add/update server
            server_config = {'command': new_command}
            if new_args:
                server_config['args'] = new_args.split() if isinstance(new_args, str) else new_args
            if new_env:
                server_config['env'] = new_env
            
            self.mcp_config[new_name] = server_config
            self.paused_servers.discard(new_name)
            self.refresh_server_list()
            self.status_var.set(f"Updated server: {new_name}")
    
    def remove_server(self):
        """Remove selected MCP server"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a server to remove")
            return
        
        item = self.tree.item(selection[0])
        name = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove server '{name}' completely?"):
            self.mcp_config.pop(name, None)
            self.paused_servers.discard(name)
            self.refresh_server_list()
            self.status_var.set(f"Removed server: {name}")
    
    def toggle_pause(self):
        """Toggle pause status of selected server"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a server to pause/resume")
            return
        
        item = self.tree.item(selection[0])
        name = item['values'][0]
        
        if name in self.paused_servers:
            # Resume: move from paused to active
            self.paused_servers.remove(name)
            if name not in self.mcp_config:
                # This shouldn't happen, but just in case
                messagebox.showwarning("Warning", f"Cannot resume '{name}': configuration lost")
                return
            self.status_var.set(f"Resumed server: {name}")
        else:
            # Pause: keep config but mark as paused
            if name in self.mcp_config:
                self.paused_servers.add(name)
                self.status_var.set(f"Paused server: {name}")
            else:
                messagebox.showwarning("Warning", f"Cannot pause '{name}': not found in configuration")
                return
        
        self.refresh_server_list()
    
    def get_actual_config_for_save(self):
        """Get the configuration that should be saved (excluding paused servers)"""
        return {name: config for name, config in self.mcp_config.items() 
                if name not in self.paused_servers}
    
    def save_config(self):
        """Save configuration to JSON file (excluding paused servers)"""
        try:
            self.log("Starting save config process...")
            
            # Create backup first
            if self.config_path.exists():
                backup_path = self.backup_dir / f"claude_desktop_config_backup_{int(os.path.getmtime(self.config_path))}.json"
                shutil.copy2(self.config_path, backup_path)
                self.log(f"Backup created: {backup_path}")
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.log(f"Config directory created/verified: {self.config_path.parent}")
            
            # Load existing config or create new one
            config = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self.log("Loaded existing config file")
                except Exception as e:
                    self.log(f"Error loading existing config: {e}")
                    config = {}
            
            # Update MCP servers (excluding paused ones)
            active_servers = self.get_actual_config_for_save()
            config['mcpServers'] = active_servers
            
            self.log(f"Active servers to save: {active_servers}")
            self.log(f"Full config to save: {config}")
            
            # Save config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            active_count = len(config['mcpServers'])
            paused_count = len(self.paused_servers)
            
            self.log(f"Config saved successfully. Active: {active_count}, Paused: {paused_count}")
            self.status_var.set(f"Saved {active_count} active servers ({paused_count} paused)")
            messagebox.showinfo("Success", f"Configuration saved!\nActive: {active_count}, Paused: {paused_count}")
            
        except Exception as e:
            error_msg = f"Failed to save config: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
            self.status_var.set("Error saving config")
    
    def restart_claude(self):
        """Restart Claude Desktop application"""
        def restart_thread():
            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    # Kill existing Claude processes
                    subprocess.run(['pkill', '-f', 'Claude'], check=False)
                    
                    # Try user-defined paths first
                    claude_paths = self.user_config.get('claude_executable_paths', [])
                    # Add default paths
                    claude_paths.extend([
                        '/Applications/Claude.app',
                        '~/Applications/Claude.app'
                    ])
                    
                    for path in claude_paths:
                        expanded_path = os.path.expandvars(os.path.expanduser(path))
                        if os.path.exists(expanded_path):
                            subprocess.run(['open', '-a', expanded_path], check=True)
                            break
                    else:
                        subprocess.run(['open', '-a', 'Claude'], check=True)
                        
                elif system == "Windows":
                    # Kill existing Claude processes
                    subprocess.run(['taskkill', '/f', '/im', 'Claude.exe'], check=False)
                    
                    # Try user-defined paths first
                    claude_paths = self.user_config.get('claude_executable_paths', [])
                    # Add default paths
                    claude_paths.extend([
                        r'%LOCALAPPDATA%\AnthropicClaude\Claude.exe',
                        r'%LOCALAPPDATA%\Programs\Claude\Claude.exe',
                        r'%PROGRAMFILES%\Claude\Claude.exe',
                        r'%PROGRAMFILES(X86)%\Claude\Claude.exe'
                    ])
                    
                    for path in claude_paths:
                        expanded_path = os.path.expandvars(path)
                        if os.path.exists(expanded_path):
                            subprocess.Popen([expanded_path])
                            break
                    else:
                        raise FileNotFoundError("Claude Desktop executable not found")
                        
                else:  # Linux
                    subprocess.run(['pkill', '-f', 'claude'], check=False)
                    
                    # Try user-defined paths first
                    claude_paths = self.user_config.get('claude_executable_paths', [])
                    # Add default paths
                    claude_paths.extend([
                        '/usr/bin/claude',
                        '/usr/local/bin/claude',
                        '~/.local/bin/claude',
                        '/opt/Claude/claude',
                        '/snap/bin/claude'
                    ])
                    
                    for path in claude_paths:
                        expanded_path = os.path.expanduser(path)
                        if os.path.exists(expanded_path):
                            subprocess.Popen([expanded_path])
                            break
                    else:
                        # Try just 'claude' in PATH
                        subprocess.run(['claude'], check=True)
                
                self.root.after(0, lambda: self.status_var.set("Claude Desktop restarted"))
                self.root.after(0, lambda: self.log("Claude Desktop restarted successfully"))
                
            except Exception as e:
                error_msg = f"Failed to restart Claude Desktop: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    f"{error_msg}\nYou may need to restart it manually or check your executable paths in Settings."))
                self.root.after(0, lambda: self.status_var.set("Failed to restart Claude Desktop"))
                self.root.after(0, lambda: self.log(error_msg))
        
        if messagebox.askyesno("Confirm", "This will restart Claude Desktop. Continue?"):
            self.status_var.set("Restarting Claude Desktop...")
            self.log("Attempting to restart Claude Desktop...")
            threading.Thread(target=restart_thread, daemon=True).start()


class ServerDialog:
    def __init__(self, parent, title, name="", command="", args="", env=None):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        main_frame.columnconfigure(1, weight=1)
        
        # Server name
        ttk.Label(main_frame, text="Server Name:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Command
        ttk.Label(main_frame, text="Command:").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.command_var = tk.StringVar(value=command)
        command_entry = ttk.Entry(main_frame, textvariable=self.command_var, width=40)
        command_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Arguments
        ttk.Label(main_frame, text="Arguments:").grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        self.args_var = tk.StringVar(value=args)
        args_entry = ttk.Entry(main_frame, textvariable=self.args_var, width=40)
        args_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Environment variables
        ttk.Label(main_frame, text="Environment Variables:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=(0, 10))
        
        env_frame = ttk.Frame(main_frame)
        env_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        env_frame.columnconfigure(0, weight=1)
        env_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        self.env_text = tk.Text(env_frame, height=10, width=40)
        env_scrollbar = ttk.Scrollbar(env_frame, orient=tk.VERTICAL, command=self.env_text.yview)
        self.env_text.configure(yscrollcommand=env_scrollbar.set)
        
        self.env_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        env_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Populate environment variables
        if env:
            env_lines = [f"{k}={v}" for k, v in env.items()]
            self.env_text.insert('1.0', '\n'.join(env_lines))
        
        # Help text
        help_text = "Enter environment variables one per line in format: KEY=value"
        ttk.Label(main_frame, text=help_text, font=('Arial', 8), foreground='gray').grid(
            row=4, column=1, sticky=tk.W, pady=(5, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT)
        
        # Bind Enter key to OK (but not when in text widget)
        self.dialog.bind('<Return>', lambda e: self.ok_clicked() if e.widget != self.env_text else None)
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
        
        # Focus on name field
        name_entry.focus_set()
        if name:  # If editing, select all text
            name_entry.select_range(0, tk.END)
    
    def parse_env_vars(self, text):
        """Parse environment variables from text"""
        env = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
        return env
    
    def ok_clicked(self):
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()
        args = self.args_var.get().strip()
        env_text = self.env_text.get('1.0', tk.END).strip()
        
        if not name:
            messagebox.showerror("Error", "Server name is required")
            return
        
        if not command:
            messagebox.showerror("Error", "Command is required")
            return
        
        env = self.parse_env_vars(env_text) if env_text else {}
        
        self.result = (name, command, args, env)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        self.dialog.destroy()


def main():
    # Enable console output on Windows
    if platform.system() == "Windows":
        try:
            import sys
            import io
            # Allocate a console for this GUI application
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.AllocConsole()
            
            # Redirect stdout and stderr to console
            sys.stdout = io.TextIOWrapper(io.FileIO(1, "wb", closefd=False), encoding='utf-8')
            sys.stderr = io.TextIOWrapper(io.FileIO(2, "wb", closefd=False), encoding='utf-8')
            print("Console allocated successfully")
        except Exception as e:
            print(f"Could not allocate console: {e}")
    
    root = tk.Tk()
    
    # Set theme
    style = ttk.Style()
    
    # Try to use a modern theme
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'vista' in available_themes:
        style.theme_use('vista')
    
    app = MCPManager(root)
    
    print("Starting MCP Manager application...")
    root.mainloop()


if __name__ == "__main__":
    main()