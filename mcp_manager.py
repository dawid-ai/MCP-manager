#!/usr/bin/env python3
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
    APP_LATEST_VERSION_URL = "https://raw.githubusercontent.com/dawid-ai/MCP-manager/refs/heads/feat/marketplace-and-version-check/mcp_manager_ver.txt"
    APP_RELEASES_PAGE_URL = "https://github.com/dawid-ai/MCP-manager"

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
        #self.marketplace_db_path = Path.home() / ".mcp_manager_data" / "marketplace.db"
        self.marketplace_db_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "marketplace.db")))
        self.marketplace_db_url = "https://github.com/dawid-ai/MCP-manager/raw/refs/heads/feat/marketplace-and-version-check/marketplace.db"  # Placeholder
        self.marketplace_version_url = "https://raw.githubusercontent.com/dawid-ai/MCP-manager/refs/heads/feat/marketplace-and-version-check/marketplace_ver.txt"  # Placeholder
        self.marketplace_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.mcp_config = {}
        self.paused_servers = set()  # Servers that are paused (not in config but saved in our tool)
        self.selected_marketplace_server_details = None # For storing full details of selected marketplace server
        self.has_unsaved_changes = False
        
        # Create GUI
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_app)
        self.log(f"MCP Manager started")
        self.log(f"Config path: {self.config_path}")
        self.log(f"Config exists: {self.config_path.exists()}")
        self.load_config()
        self.refresh_server_list()
        self.check_db_version()
        self.load_marketplace_servers()
        self.check_app_version() # Check for app updates

    # Placeholder methods for new marketplace DB management buttons
    def add_new_marketplace_server(self):
        self.log("Opening Add New Marketplace Server dialog...")
        dialog = MarketplaceServerDialog(self.root, title="Add New Marketplace Server")
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            (name, description, instructions, owner_name, owner_link, 
             repo_link, command, args_json_str, env_json_str) = dialog.result
            
            self.log(f"Attempting to add new marketplace server: {name}")
            conn = None
            try:
                conn = sqlite3.connect(self.marketplace_db_path)
                cursor = conn.cursor()
                # Ensure your table and column names match exactly
                cursor.execute("""
                    INSERT INTO servers (name, description, instructions, owner_name, owner_link, 
                                         repo_link, command, args, env_vars, date_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, description, instructions, owner_name, owner_link, 
                      repo_link, command, args_json_str, env_json_str, datetime.now().isoformat()))
                conn.commit()
                self.log(f"Successfully added server '{name}' to marketplace.db")
                messagebox.showinfo("Success", f"Server '{name}' added to marketplace.")
                self.update_marketplace_db_version() # Update DB version
                self.load_marketplace_servers() # Refresh treeview
            except sqlite3.IntegrityError as e: # Catch issues like UNIQUE constraint violation for name
                self.log(f"SQLite IntegrityError adding server '{name}': {e}")
                messagebox.showerror("Database Error", f"Could not add server '{name}'. It might already exist or there's a data conflict: {e}")
            except sqlite3.Error as e:
                self.log(f"SQLite error adding server '{name}': {e}")
                messagebox.showerror("Database Error", f"Failed to add server to marketplace: {e}")
            finally:
                if conn:
                    conn.close()
        else:
            self.log("Add new marketplace server dialog cancelled.")

    def edit_selected_marketplace_server(self):
        self.log("Attempting to edit selected marketplace server...")
        selection = self.marketplace_tree.selection()
        if not selection:
            messagebox.showwarning("No Server Selected", "Please select a server from the marketplace list to edit.")
            self.log("Edit marketplace server failed: No server selected.")
            return

        item = self.marketplace_tree.item(selection[0])
        selected_server_name_in_tree = item['values'][0]
        self.log(f"Selected server for editing: {selected_server_name_in_tree}")

        conn = None
        original_server_data = None
        server_id = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()
            # Fetch all columns including the primary key 'id'
            cursor.execute("""
                SELECT id, name, description, instructions, owner_name, owner_link, 
                       repo_link, command, args, env_vars 
                FROM servers WHERE name = ?
            """, (selected_server_name_in_tree,))
            original_server_data_tuple = cursor.fetchone()

            if not original_server_data_tuple:
                messagebox.showerror("Error", f"Could not fetch details for server '{selected_server_name_in_tree}' from the database.")
                self.log(f"Failed to fetch details for '{selected_server_name_in_tree}'.")
                return
            
            # Store data in a dictionary for easier access, and get column names
            column_names = [desc[0] for desc in cursor.description]
            original_server_data = dict(zip(column_names, original_server_data_tuple))
            server_id = original_server_data['id'] # Crucial for WHERE clause in UPDATE

            self.log(f"Fetched data for editing (ID: {server_id}): {original_server_data}")

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error fetching server details: {e}")
            self.log(f"SQLite error fetching details for '{selected_server_name_in_tree}': {e}")
            if conn:
                conn.close()
            return
        finally:
            if conn and original_server_data is None: # Ensure connection is closed if we exited early
                conn.close()


        # Ensure args and env_vars are not None before passing to dialog
        args_str = original_server_data.get('args', '[]') or '[]'
        env_vars_str = original_server_data.get('env_vars', '{}') or '{}'

        dialog = MarketplaceServerDialog(
            self.root, 
            title=f"Edit Marketplace Server: {original_server_data['name']}",
            name=original_server_data['name'],
            description=original_server_data.get('description', ''),
            instructions=original_server_data.get('instructions', ''),
            owner_name=original_server_data.get('owner_name', ''),
            owner_link=original_server_data.get('owner_link', ''),
            repo_link=original_server_data.get('repo_link', ''),
            command=original_server_data.get('command', ''),
            args_str=args_str,
            env_vars_str=env_vars_str
        )
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            (new_name, new_description, new_instructions, new_owner_name, 
             new_owner_link, new_repo_link, new_command, 
             new_args_json_str, new_env_json_str) = dialog.result
            
            self.log(f"Attempting to update marketplace server ID: {server_id} (Original Name: {original_server_data['name']}, New Name: {new_name})")
            try:
                # Re-use connection if still open from fetch, or reconnect
                if conn is None or conn.total_changes == -1: # Check if connection was closed or is unusable
                    conn = sqlite3.connect(self.marketplace_db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE servers 
                    SET name=?, description=?, instructions=?, owner_name=?, owner_link=?, 
                        repo_link=?, command=?, args=?, env_vars=?
                    WHERE id = ?
                """, (new_name, new_description, new_instructions, new_owner_name, 
                      new_owner_link, new_repo_link, new_command, 
                      new_args_json_str, new_env_json_str, server_id))
                conn.commit()
                self.log(f"Successfully updated server ID: {server_id} in marketplace.db")
                messagebox.showinfo("Success", f"Server '{new_name}' updated in marketplace.")
                self.update_marketplace_db_version() # Update DB version
                self.load_marketplace_servers() # Refresh treeview
            except sqlite3.IntegrityError as e:
                 self.log(f"SQLite IntegrityError updating server ID {server_id}: {e}")
                 messagebox.showerror("Database Error", f"Could not update server '{new_name}'. The name might already exist or there's a data conflict: {e}")
            except sqlite3.Error as e:
                self.log(f"SQLite error updating server ID {server_id}: {e}")
                messagebox.showerror("Database Error", f"Failed to update server in marketplace: {e}")
            finally:
                if conn:
                    conn.close()
        else:
            self.log(f"Edit marketplace server dialog cancelled for server ID: {server_id}.")
            if conn: # Ensure connection is closed if dialog was cancelled
                 conn.close()


    def remove_selected_marketplace_server(self):
        self.log("Attempting to remove selected marketplace server...")
        selection = self.marketplace_tree.selection()
        if not selection:
            messagebox.showwarning("No Server Selected", "Please select a server from the marketplace list to remove.")
            self.log("Remove marketplace server failed: No server selected.")
            return

        item = self.marketplace_tree.item(selection[0])
        server_name_to_remove = item['values'][0] # Name is the first value in the tree row

        if not messagebox.askyesno("Confirm Removal", 
                                   f"Are you sure you want to remove the server '{server_name_to_remove}' from the marketplace? This action cannot be undone.",
                                   icon='warning'):
            self.log(f"User cancelled removal of server: {server_name_to_remove}")
            return

        self.log(f"User confirmed removal of server: {server_name_to_remove}")
        conn = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servers WHERE name = ?", (server_name_to_remove,))
            conn.commit()

            if cursor.rowcount > 0:
                self.log(f"Successfully removed server '{server_name_to_remove}' from marketplace.db. Rows affected: {cursor.rowcount}")
                messagebox.showinfo("Success", f"Server '{server_name_to_remove}' removed successfully from the marketplace.")
                self.update_marketplace_db_version() # Update DB version
            else:
                self.log(f"No server found with name '{server_name_to_remove}' to remove, though it was selected. Rows affected: {cursor.rowcount}")
                messagebox.showwarning("Not Found", f"Server '{server_name_to_remove}' was not found in the database for removal, it might have been removed already.")
            
            self.load_marketplace_servers() # Refresh treeview
            self.server_details_text.config(state='normal') # Clear details text
            self.server_details_text.delete('1.0', tk.END)
            self.server_details_text.config(state='disabled')
            self.selected_marketplace_server_details = None

        except sqlite3.Error as e:
            self.log(f"SQLite error removing server '{server_name_to_remove}': {e}")
            messagebox.showerror("Database Error", f"Failed to remove server '{server_name_to_remove}' from the marketplace: {e}")
        finally:
            if conn:
                conn.close()
        
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
        bottom_frame.pack(fill='x', pady=(10,0)) # Added some top padding to separate from treeview

        # Server details text area (now at the top of bottom_frame)
        self.server_details_text = scrolledtext.ScrolledText(bottom_frame, height=6, wrap=tk.WORD, state='disabled')
        self.server_details_text.pack(fill='x', expand=True, side=tk.TOP, pady=(0,10))

        # Frame for all action buttons
        actions_frame = ttk.Frame(bottom_frame)
        actions_frame.pack(fill='x')

        # Frame for DB management buttons (aligned left)
        db_actions_frame = ttk.Frame(actions_frame)
        db_actions_frame.pack(side=tk.LEFT)

        self.add_new_db_server_button = ttk.Button(db_actions_frame, text="Add New Server", command=self.add_new_marketplace_server)
        self.add_new_db_server_button.pack(side=tk.LEFT, padx=(0, 5))

        self.edit_selected_db_server_button = ttk.Button(db_actions_frame, text="Edit Selected Server", command=self.edit_selected_marketplace_server)
        self.edit_selected_db_server_button.pack(side=tk.LEFT, padx=(0, 5))

        self.remove_selected_db_server_button = ttk.Button(db_actions_frame, text="Remove Selected Server", command=self.remove_selected_marketplace_server)
        self.remove_selected_db_server_button.pack(side=tk.LEFT, padx=(0,5))
        
        # Existing button to add to local MCP Manager (aligned right)
        self.add_from_marketplace_button = ttk.Button(actions_frame, text="Add to MCP Manager", command=self.add_server_from_marketplace)
        self.add_from_marketplace_button.pack(side=tk.RIGHT, anchor='e')


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
            local_version_string = self.get_marketplace_db_version() # Use new method
        else:
            local_version_string = "Not found"
            self.log("Local DB file does not exist.")

        if hasattr(self, 'local_db_version_label'): # Ensure GUI is initialized
            self.local_db_version_label.config(text=f"Local DB: {local_version_string}")

        self.log(f"DB Versions - Local: {local_version_string}, Remote: {remote_version_string}")

    def get_marketplace_db_version(self) -> str:
        """Gets the version from the marketplace DB, initializes if not present."""
        default_version = "1.0.0"
        conn = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()
            
            # Ensure metadata table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

            cursor.execute("SELECT value FROM metadata WHERE key = 'version'")
            row = cursor.fetchone()
            if row:
                self.log(f"Found local DB version in get_marketplace_db_version: {row[0]}")
                return row[0]
            else:
                self.log("No version key found in metadata. Initializing to 1.0.0.")
                # Key not found, insert default version
                cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('version', ?)", (default_version,))
                conn.commit()
                return default_version
        except sqlite3.Error as e:
            self.log(f"SQLite error in get_marketplace_db_version: {e}. Returning default version.")
            return default_version # Fallback on error
        finally:
            if conn:
                conn.close()

    def update_marketplace_db_version(self):
        """Increments the patch number of the marketplace DB version."""
        self.log("Attempting to update marketplace DB version...")
        current_version_str = self.get_marketplace_db_version()
        
        new_version_str = ""
        try:
            parts = current_version_str.split('.')
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                major, minor, patch = map(int, parts)
                patch += 1
                new_version_str = f"{major}.{minor}.{patch}"
            else:
                # If format is unexpected, try to append ".1" or set a new default
                self.log(f"Unexpected version format '{current_version_str}'. Attempting to reset or append.")
                if current_version_str == "1.0.0" or not current_version_str : # Handles initial or corrupted
                     new_version_str = "1.0.1"
                else: # Append .1 if it's some other non-standard string
                     new_version_str = f"{current_version_str}.1" 
                     # Or more safely, always reset to a known good next version
                     # new_version_str = "1.0.1" # if previous was "1.0.0"
        except Exception as e:
            self.log(f"Error parsing version string '{current_version_str}': {e}. Setting to default '1.0.1'.")
            new_version_str = "1.0.1" # Fallback

        if not new_version_str: # Should not happen if logic above is correct
            self.log("Failed to determine new version string. Aborting update.")
            return

        conn = None
        try:
            conn = sqlite3.connect(self.marketplace_db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('version', ?)", (new_version_str,))
            conn.commit()
            self.log(f"Marketplace DB version updated from '{current_version_str}' to '{new_version_str}'.")
            # Update the label in the UI as well
            if hasattr(self, 'local_db_version_label'):
                self.local_db_version_label.config(text=f"Local DB: {new_version_str}")
        except sqlite3.Error as e:
            self.log(f"SQLite error updating DB version: {e}")
        finally:
            if conn:
                conn.close()

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
        self.has_unsaved_changes = True

        self.refresh_server_list()  # Update the tree in the main "MCP Servers" tab
        messagebox.showinfo("Success", f"Server '{name}' added/updated in MCP Manager.")
        self.log(f"Server '{name}' successfully added/updated from marketplace with config: {server_config}")

    def open_json_import_dialog_for_mcp(self):
        self.log("Opening Import MCP Server from JSON dialog...")
        dialog = MCPJSONImportDialog(self.root, title="Import MCP Server from JSON")
        # self.root.wait_window(dialog.dialog) # simpledialog.Dialog handles this

        if dialog.result:
            server_name, server_config = dialog.result
            self.log(f"Attempting to import server: {server_name} with config: {server_config}")

            if server_name in self.mcp_config:
                if not messagebox.askyesno("Confirm Overwrite",
                                           f"Server '{server_name}' already exists in your MCP Servers. Overwrite it?",
                                           parent=self.root): # Ensure dialog is parented correctly
                    self.log(f"User cancelled overwriting existing server '{server_name}'.")
                    return
                self.log(f"User confirmed overwriting existing server '{server_name}'.")

            self.mcp_config[server_name] = server_config
            self.paused_servers.discard(server_name)  # Ensure the server is active
            self.has_unsaved_changes = True

            self.refresh_server_list()
            messagebox.showinfo("Success", f"Server '{server_name}' imported successfully into MCP Manager.")
            self.log(f"Server '{server_name}' successfully imported.")
            self.status_var.set(f"Imported server: {server_name}")
        else:
            self.log("Import MCP Server from JSON dialog cancelled or no result.")

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
        ttk.Button(button_frame, text="Import from JSON", command=self.open_json_import_dialog_for_mcp).pack(side=tk.LEFT, padx=(0, 5))
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
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before reloading?",
                parent=self.root
            )
            if response is True:  # Yes
                self.save_config()
                # Proceed with reload even if save failed, as user chose to save.
            elif response is None:  # Cancel
                self.log("Reload config cancelled by user due to unsaved changes.")
                return # Abort reload
            # If False (No), proceed to reload, overwriting changes.

        try:
            self.log(f"Loading config from: {self.config_path}")
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.mcp_config = config.get('mcpServers', {})
                self.log(f"Loaded {len(self.mcp_config)} servers from config")
                self.log(f"Server names: {list(self.mcp_config.keys())}")
                self.status_var.set(f"Loaded {len(self.mcp_config)} servers from config")
                self.has_unsaved_changes = False # Reset flag after successful load
            else:
                self.mcp_config = {}
                self.log("Config file not found - will create new one")
                self.status_var.set("Config file not found - will create new one")
                self.has_unsaved_changes = False # No config to have unsaved changes against

            self.refresh_server_list() # Refresh list after loading

        except Exception as e:
            error_msg = f"Failed to load config: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            messagebox.showerror("Error", f"Failed to load config: {str(e)}")
            self.status_var.set("Error loading config")
        # If loading failed partway, changes might still be considered unsaved
        # However, typical case is loading successfully, which resets unsaved status.
        # self.has_unsaved_changes = False # This is now at the end of successful load

    def on_closing_app(self):
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before closing?",
                parent=self.root
            )
            if response is True:  # Yes
                self.save_config() # Attempt to save
                self.root.destroy()
            elif response is False:  # No
                self.root.destroy()
            else:  # Cancel
                return  # Do nothing, keep app open
        else:
            self.root.destroy()

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
            self.has_unsaved_changes = False # Reset flag after successful save
            
        except Exception as e:
            error_msg = f"Failed to save config: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
            self.status_var.set("Error saving config")
            # Do not reset has_unsaved_changes if save failed
    
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
            self.has_unsaved_changes = True
            
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
            self.has_unsaved_changes = True
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
            self.has_unsaved_changes = True
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
        
        self.has_unsaved_changes = True
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

class MCPJSONImportDialog(simpledialog.Dialog):
    def body(self, master):
        self.master = master # Keep a reference for parenting messageboxes
        master.pack_forget() # Hide the default simpledialog frame

        # Dialog settings
        self.parent.title("Import MCP Server from JSON")
        # self.parent.geometry("500x400") # Adjust as needed

        # Main frame for content
        # Using self.parent as it's the Toplevel window
        content_frame = ttk.Frame(self.parent, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content_frame,
                  text="Paste JSON for one or more MCP servers below.",
                  wraplength=480).pack(pady=5, anchor=tk.W)
        ttk.Label(content_frame,
                  text="Expected format: {\"mcpServers\": {\"server_name\": {\"command\": ..., \"args\": ..., \"env\": ...}}}",
                  font=('Arial', 8), foreground='gray', wraplength=480).pack(pady=(0,10), anchor=tk.W)

        self.json_text_widget = scrolledtext.ScrolledText(content_frame, width=60, height=15, wrap=tk.WORD)
        self.json_text_widget.pack(fill=tk.BOTH, expand=True, pady=5)
        self.json_text_widget.focus_set()

        self.result = None
        return self.json_text_widget # initial focus

    def buttonbox(self):
        # Overriding buttonbox to use ttk buttons and place them in our content_frame
        # The master frame from simpledialog.Dialog is not used directly for content.
        # Instead, we add buttons to the Toplevel window (self.parent) or a frame within it.

        # Find the content_frame we created in body()
        # This assumes content_frame is the first child of self.parent, which might be fragile.
        # A better way would be to store content_frame as self.content_frame in body().
        # For now, let's assume self.parent is where we want to add the button box.
        # We will add buttons to a new frame at the bottom of self.parent (Toplevel)

        box = ttk.Frame(self.parent, padding=(0,0,0,10)) # Add padding only at the bottom

        w = ttk.Button(box, text="Import", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack(side=tk.BOTTOM) # Pack the button box at the bottom of the dialog

    def validate(self):
        json_string = self.json_text_widget.get("1.0", tk.END).strip()
        if not json_string:
            messagebox.showerror("Error", "JSON input is empty.", parent=self.parent)
            return 0

        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON: {e}", parent=self.parent)
            return 0

        if not isinstance(data, dict) or "mcpServers" not in data:
            messagebox.showerror("JSON Error", "JSON must be an object with an 'mcpServers' key.", parent=self.parent)
            return 0

        mcp_servers = data["mcpServers"]
        if not isinstance(mcp_servers, dict) or not mcp_servers:
            messagebox.showerror("JSON Error", "'mcpServers' must be a non-empty object.", parent=self.parent)
            return 0

        # Extract the first server
        # (In a more complex scenario, you might let the user choose if multiple are present)
        server_name = list(mcp_servers.keys())[0]
        server_config = mcp_servers[server_name]

        if not isinstance(server_config, dict) or "command" not in server_config:
            messagebox.showerror("JSON Error", f"Server '{server_name}' is missing 'command' or is not an object.", parent=self.parent)
            return 0

        # Validate args and env structure (optional but good practice)
        if "args" in server_config and not isinstance(server_config["args"], list):
            messagebox.showerror("JSON Error", f"Server '{server_name}' 'args' must be a list.", parent=self.parent)
            return 0
        if "env" in server_config and not isinstance(server_config["env"], dict):
            messagebox.showerror("JSON Error", f"Server '{server_name}' 'env' must be an object.", parent=self.parent)
            return 0

        # Store the result
        self.result = (server_name, {
            "command": server_config.get("command"),
            "args": server_config.get("args", []), # Default to empty list
            "env": server_config.get("env", {})    # Default to empty dict
        })

        if len(mcp_servers) > 1:
             messagebox.showinfo("Info", f"Multiple servers found in JSON. Importing the first one: '{server_name}'.", parent=self.parent)

        return 1 # Validation successful

    # apply() is called by ok() if validate() is successful
    # We don't need to do anything special here as result is already set in validate()
    # def apply(self):
    #     pass


# ServerDialog class for adding/editing servers manually
        
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

class MarketplaceServerDialog:
    def __init__(self, parent, title, name="", description="", instructions="", 
                 owner_name="", owner_link="", repo_link="", command="", 
                 args_str='[]', env_vars_str='{}'):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        # Adjusted height for JSON import section
        self.dialog.geometry("700x950") 
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (800 // 2)
        self.dialog.geometry(f"700x800+{x}+{y}")
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        main_frame.columnconfigure(1, weight=1) # Allow second column to expand

        current_row = 0

        # Server Name
        ttk.Label(main_frame, text="Server Name*:").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=60)
        name_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        current_row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=current_row, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.desc_text = tk.Text(main_frame, height=4, width=60, wrap=tk.WORD)
        self.desc_text.insert('1.0', description)
        self.desc_text.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        main_frame.rowconfigure(current_row, weight=0) # Adjust weight as needed
        current_row += 1

        # Instructions
        ttk.Label(main_frame, text="Instructions:").grid(row=current_row, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.instr_text = tk.Text(main_frame, height=6, width=60, wrap=tk.WORD)
        self.instr_text.insert('1.0', instructions)
        self.instr_text.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        main_frame.rowconfigure(current_row, weight=0) # Adjust weight as needed
        current_row += 1

        # Owner Name
        ttk.Label(main_frame, text="Owner Name:").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.owner_name_var = tk.StringVar(value=owner_name)
        ttk.Entry(main_frame, textvariable=self.owner_name_var, width=60).grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        current_row += 1

        # Owner Link
        ttk.Label(main_frame, text="Owner Link (URL):").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.owner_link_var = tk.StringVar(value=owner_link)
        ttk.Entry(main_frame, textvariable=self.owner_link_var, width=60).grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        current_row += 1

        # Repository Link
        ttk.Label(main_frame, text="Repo Link (URL):").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.repo_link_var = tk.StringVar(value=repo_link)
        ttk.Entry(main_frame, textvariable=self.repo_link_var, width=60).grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        current_row += 1
        
        # Command
        ttk.Label(main_frame, text="Command*:").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.command_var = tk.StringVar(value=command)
        ttk.Entry(main_frame, textvariable=self.command_var, width=60).grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        current_row += 1

        # Arguments (JSON list string)
        ttk.Label(main_frame, text="Arguments (JSON list):").grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        self.args_var = tk.StringVar(value=args_str)
        args_entry = ttk.Entry(main_frame, textvariable=self.args_var, width=60)
        args_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(main_frame, text="Example: [\"--port\", \"8000\", \"--verbose\"]", font=('Arial', 8), foreground='gray').grid(
            row=current_row + 1, column=1, sticky=tk.W, pady=(0,10))
        current_row += 2


        # Environment Variables (JSON object string)
        ttk.Label(main_frame, text="Environment Variables (JSON object):").grid(row=current_row, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        env_frame = ttk.Frame(main_frame)
        env_frame.grid(row=current_row, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        env_frame.columnconfigure(0, weight=1)
        env_frame.rowconfigure(0, weight=1)
        # main_frame.rowconfigure(current_row, weight=1) # Make env_text area expand if needed

        self.env_text = tk.Text(env_frame, height=5, width=60) # Adjusted height
        self.env_text.insert('1.0', env_vars_str)
        env_scrollbar = ttk.Scrollbar(env_frame, orient=tk.VERTICAL, command=self.env_text.yview)
        self.env_text.configure(yscrollcommand=env_scrollbar.set)
        self.env_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        env_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        ttk.Label(main_frame, text="Example: {\"API_KEY\": \"your_key\", \"DEBUG\": \"true\"}", font=('Arial', 8), foreground='gray').grid(
            row=current_row + 1, column=1, sticky=tk.W, pady=(0,10))
        current_row += 2
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        # Ensure button_frame is placed below all other content
        button_frame.grid(row=current_row, column=0, columnspan=2, pady=(15, 0), sticky=tk.S)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT)

        current_row +=1 # Move to next row for JSON import section

        # --- JSON Import Section ---
        json_import_frame = ttk.LabelFrame(main_frame, text="Import from JSON", padding="10")
        json_import_frame.grid(row=current_row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        json_import_frame.columnconfigure(0, weight=1) # Allow text widget to expand

        ttk.Label(json_import_frame, text="Paste MCP Server JSON here (expects format: {\"mcpServers\": {\"your_server_name\": {...}}}):").pack(anchor='w', pady=(0,5))
        
        self.json_import_text = tk.Text(json_import_frame, height=7, width=80) # Adjusted width to match other fields roughly
        self.json_import_text.pack(fill='x', expand=True, pady=(0,5))

        self.parse_json_button = ttk.Button(json_import_frame, text="Parse JSON and Populate Fields", command=self.parse_and_populate_from_json)
        self.parse_json_button.pack(pady=(5,0))
        
        self.dialog.bind('<Return>', lambda e: self.ok_clicked() if not isinstance(e.widget, tk.Text) else None)
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
        
        name_entry.focus_set()

    def parse_and_populate_from_json(self):
        json_string = self.json_import_text.get('1.0', tk.END).strip()
        if not json_string:
            messagebox.showwarning("Empty JSON", "JSON input is empty.", parent=self.dialog)
            return

        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON: {e}", parent=self.dialog)
            return

        if not isinstance(data, dict):
            messagebox.showerror("JSON Error", "Top level JSON must be an object.", parent=self.dialog)
            return

        if "mcpServers" not in data:
            messagebox.showerror("JSON Error", "Missing 'mcpServers' key in JSON.", parent=self.dialog)
            return

        mcp_servers = data["mcpServers"]
        if not isinstance(mcp_servers, dict):
            messagebox.showerror("JSON Error", "'mcpServers' value must be an object.", parent=self.dialog)
            return
        
        if not mcp_servers:
            messagebox.showwarning("Empty Server List", "'mcpServers' object contains no server entries.", parent=self.dialog)
            return

        server_names = list(mcp_servers.keys())
        server_name_to_import = server_names[0]
        server_data = mcp_servers[server_name_to_import]

        if len(server_names) > 1:
            # In a real scenario, you might prompt the user to choose one.
            # For now, we just take the first one and inform the user.
            print(f"Multiple servers found in JSON. Importing the first one: '{server_name_to_import}'")
            messagebox.showinfo("Multiple Servers", 
                                f"Multiple servers found. Importing the first one: '{server_name_to_import}'.", 
                                parent=self.dialog)


        # Extract data, providing defaults for safety
        name = server_name_to_import # Key is the name
        command = server_data.get("command", "")
        args_list = server_data.get("args", [])
        env_dict = server_data.get("env", {})

        if not isinstance(args_list, list):
            messagebox.showerror("JSON Error", f"Server '{name}' 'args' must be a list.", parent=self.dialog)
            return
        if not isinstance(env_dict, dict):
            messagebox.showerror("JSON Error", f"Server '{name}' 'env' must be an object.", parent=self.dialog)
            return
            
        # Populate the fields
        self.name_var.set(name)
        self.command_var.set(command)
        self.args_var.set(json.dumps(args_list)) # Store as JSON string
        
        self.env_text.delete('1.0', tk.END)
        self.env_text.insert('1.0', json.dumps(env_dict)) # Store as JSON string
        
        # Description, Instructions, Owner, Repo are not typically in this JSON, so they are NOT cleared/updated.
        # User is expected to fill them if needed.

        messagebox.showinfo("Success", 
                            f"Fields populated from JSON for server '{name}'.\n"
                            "Please review, fill any additional fields (like description, instructions), and click OK.", 
                            parent=self.dialog)


    def ok_clicked(self):
        name = self.name_var.get().strip()
        description = self.desc_text.get('1.0', tk.END).strip()
        instructions = self.instr_text.get('1.0', tk.END).strip()
        owner_name = self.owner_name_var.get().strip()
        owner_link = self.owner_link_var.get().strip()
        repo_link = self.repo_link_var.get().strip()
        command = self.command_var.get().strip()
        args_json_str = self.args_var.get().strip()
        env_json_str = self.env_text.get('1.0', tk.END).strip()

        if not name:
            messagebox.showerror("Error", "Server Name is required.", parent=self.dialog)
            return
        if not command:
            messagebox.showerror("Error", "Command is required.", parent=self.dialog)
            return

        # Validate Args JSON
        try:
            args_val = json.loads(args_json_str)
            if not isinstance(args_val, list):
                messagebox.showerror("Error", "Arguments must be a valid JSON list (e.g., [\"--flag\"]).", parent=self.dialog)
                return
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Arguments field contains invalid JSON.", parent=self.dialog)
            return
        
        # Validate Env Vars JSON
        try:
            env_val = json.loads(env_json_str)
            if not isinstance(env_val, dict):
                messagebox.showerror("Error", "Environment Variables must be a valid JSON object (e.g., {\"KEY\": \"value\"}).", parent=self.dialog)
                return
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Environment Variables field contains invalid JSON.", parent=self.dialog)
            return

        self.result = (name, description, instructions, owner_name, owner_link, 
                       repo_link, command, args_json_str, env_json_str)
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