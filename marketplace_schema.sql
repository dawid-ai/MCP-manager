-- Schema for the MCP Manager Marketplace Database (marketplace.db)

-- Table to store metadata, primarily the database version
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY, -- The key for the metadata entry (e.g., 'version')
    value TEXT            -- The value for the metadata entry (e.g., '1.0.0')
);

-- Insert an initial version for the database.
-- Replace '1.0.0' with your desired starting version.
INSERT INTO metadata (key, value) VALUES ('version', '1.0.0');

-- Table to store the list of MCP servers available in the marketplace
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier for each server entry
    name TEXT UNIQUE NOT NULL,            -- Display name of the server (must be unique)
    description TEXT,                     -- A brief description of the server's purpose
    instructions TEXT,                    -- Detailed instructions on how to use or set up the server
    owner_name TEXT,                      -- Name of the server's author or maintainer
    owner_link TEXT,                      -- URL to the owner's website, profile, or contact page
    repo_link TEXT,                       -- URL to the server's source code repository (e.g., GitHub)
    command TEXT NOT NULL,                -- The command needed to run the MCP server
    args TEXT,                            -- JSON string array of arguments for the command (e.g., "["--port", "8080"]"). Store as '[]' if no arguments.
    env_vars TEXT                         -- JSON string object of environment variables (e.g., "{\"API_KEY\": \"secret\"}"). Store as '{}' if no environment variables.
);

-- Example of how to insert a server (optional, for reference):
/*
INSERT INTO servers (name, description, instructions, owner_name, owner_link, repo_link, command, args, env_vars)
VALUES (
    'Example Server',
    'A simple example server for demonstration.',
    '1. Download the server executable.
2. Run it.
3. Connect via MCP Manager.',
    'John Doe',
    'https://example.com/johndoe',
    'https://github.com/johndoe/example-server',
    'python example_server.py',
    '["--debug", "--port", "7777"]',
    '{"LOG_LEVEL": "INFO"}'
);
*/
