# Rappel Conso MCP Server

A Model Context Protocol (MCP) server for accessing French product recall data from the RappelConso API.

## Overview

This MCP server provides tools to query the French government's product recall database (RappelConso). It exposes several tools that can be used by MCP clients to search and retrieve product recall information.

## Available Tools

- `get_rappels_conso`: Retrieve product recalls with filtering and pagination
- `get_latest_rappels`: Get the most recent product recalls
- `get_categories_with_counts`: List product categories with recall counts
- `get_most_represented_category`: Find the category with the most recalls
- `get_latest_from_category`: Get recent recalls from a specific category

## Available Prompts

- `chercher_rappel_produit`: Generate a search message for a specific product

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Server

### Authentication

This server uses GitHub OAuth for authentication. You will need to create a GitHub OAuth application and set the following environment variables:

- `GITHUB_CLIENT_ID`: The client ID of your GitHub OAuth app.
- `GITHUB_CLIENT_SECRET`: The client secret of your GitHub OAuth app.
- `BASE_URL`: The public URL of your server (e.g., `https://your-server.com`). This is required for the OAuth callback to work correctly in a deployed environment.

When creating the OAuth app, you must provide the following callback URLs:
- `http://127.0.0.1:33418`
- `https://vscode.dev/redirect`

### Starting the server

```bash
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
export BASE_URL="http://localhost:8000" # Or your public URL
python server-rappel.py
```

## Testing

This project includes a comprehensive test suite to verify MCP server functionality.

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

Run all tests:
```bash
pytest test_mcp_server.py -v
```

Run specific test classes:
```bash
pytest test_mcp_server.py::TestMCPServerConfiguration -v
pytest test_mcp_server.py::TestMCPTools -v
pytest test_mcp_server.py::TestMCPPrompts -v
pytest test_mcp_server.py::TestToolFunctionality -v
pytest test_mcp_server.py::TestErrorHandling -v
```

### Test Coverage

The test suite covers:
- MCP server initialization and configuration
- Tool availability and registration
- Prompt availability and functionality
- Tool functionality with mocked API calls
- Error handling for HTTP and request errors

## License

This project provides access to public data from the French government's RappelConso database.
