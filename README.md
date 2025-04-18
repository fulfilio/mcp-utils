# mcp-utils

A Python utility package for building Model Context Protocol (MCP) servers.

![Tests](https://github.com/fulfilio/mcp-utils/actions/workflows/test.yml/badge.svg) ![PyPI - Version](https://img.shields.io/pypi/v/mcp-utils)



## Table of Contents

- [mcp-utils](#mcp-utils)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Key Features](#key-features)
  - [Installation](#installation)
  - [Requirements](#requirements)
    - [Optional Dependencies](#optional-dependencies)
  - [Usage](#usage)
    - [Basic MCP Server](#basic-mcp-server)
    - [Flask with Redis Example](#flask-with-redis-example)
    - [SQLAlchemy Transaction Handling Example](#sqlalchemy-transaction-handling-example)
  - [Connecting with MCP Clients](#connecting-with-mcp-clients)
    - [Claude Desktop](#claude-desktop)
      - [Installing via Smithery](#installing-via-smithery)
      - [Installing via PyPI](#installing-via-pypi)
  - [Contributing](#contributing)
  - [Related Projects](#related-projects)
  - [License](#license)
  - [Testing with MCP Inspector](#testing-with-mcp-inspector)
    - [Installation](#installation-1)
    - [Usage](#usage-1)

## Overview

`mcp-utils` provides utilities and helpers for building MCP-compliant servers in Python, with a focus on synchronous implementations using Flask. This package is designed for developers who want to implement MCP servers in their existing Python applications without the complexity of asynchronous code.

## Key Features

- Basic utilities for MCP server implementation
- Server-Sent Events (SSE) support
- Simple decorators for MCP endpoints
- Synchronous implementation
- HTTP protocol support
- Redis response queue
- Comprehensive Pydantic models for MCP schema
- Built-in validation and documentation

## Installation

```bash
pip install mcp-utils
```

## Requirements

- Python 3.10+
- Pydantic 2

### Optional Dependencies

- Flask (for web server)
- Gunicorn (for production deployment)
- Redis (for response queue)

## Usage

### Basic MCP Server

Here's a simple example of creating an MCP server:

```python
from mcp_utils.core import MCPServer
from mcp_utils.schema import GetPromptResult, Message, TextContent, CallToolResult

# Create a basic MCP server
mcp = MCPServer("example", "1.0")

@mcp.prompt()
def get_weather_prompt(city: str) -> GetPromptResult:
    return GetPromptResult(
        description="Weather prompt",
        messages=[
            Message(
                role="user",
                content=TextContent(
                    text=f"What is the weather like in {city}?",
                ),
            )
        ],
    )

@mcp.tool()
def get_weather(city: str) -> str:
    return "sunny"
```

### Flask with Redis Example

For production use, you can integrate the MCP server with Flask and Redis for better message handling:

```python
from flask import Flask, Response, url_for, request
import redis
from mcp_utils.queue import RedisResponseQueue

# Setup Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Create Flask app and MCP server with Redis queue
app = Flask(__name__)
mcp = MCPServer(
    "example",
    "1.0",
    response_queue=RedisResponseQueue(redis_client)
)

@app.route("/sse")
def sse():
    session_id = mcp.generate_session_id()
    messages_endpoint = url_for("message", session_id=session_id)
    return Response(
        mcp.sse_stream(session_id, messages_endpoint),
        mimetype="text/event-stream"
    )


@app.route("/message/<session_id>", methods=["POST"])
def message(session_id):
    mcp.handle_message(session_id, request.get_json())
    return "", 202


if __name__ == "__main__":
    app.run(debug=True)
```

### SQLAlchemy Transaction Handling Example

For production use, you can integrate the MCP server with Flask, Redis, and SQLAlchemy for better message handling and database transaction management:

```python
from flask import Flask, request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import redis
from mcp_utils.queue import RedisResponseQueue

# Setup Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Create engine for PostgreSQL database
engine = create_engine("postgresql://user:pass@localhost/dbname")

# Create Flask app and MCP server with Redis queue
app = Flask(__name__)
mcp = MCPServer(
    "example",
    "1.0",
    response_queue=RedisResponseQueue(redis_client)
)

@app.route("/message/<session_id>", methods=["POST"])
def message(session_id):
    with Session(engine) as session:
        try:
            mcp.handle_message(session_id, request.get_json())
            session.commit()
            return "", 202
        except Exception as e:
            session.rollback()
            raise

if __name__ == "__main__":
    app.run(debug=True)
```

For a more comprehensive example including logging setup and session management, check out the [example Flask application](https://github.com/fulfilio/mcp-utils/blob/main/examples/flask_app.py) in the repository.

## Connecting with MCP Clients

### Claude Desktop

Currently, only Claude Desktop (not claude.ai) can connect to MCP servers. As of this writing, Claude Desktop does not support MCP through SSE and only supports stdio. To connect Claude Desktop with an MCP server, you'll need to use [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy).

Configuration example for Claude Desktop:

```json
{
  "mcpServers": {
    "weather": {
      "command": "/Users/yourname/.local/bin/mcp-proxy",
      "args": ["http://127.0.0.1:9000/sse"]
    }
  }
}
```

#### Installing via Smithery

To install MCP Proxy for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-proxy):

```bash
npx -y @smithery/cli install mcp-proxy --client claude
```

#### Installing via PyPI

The stable version of the package is available on the PyPI repository. You can install it using the following command:

```bash
# Option 1: With uv (recommended)
uv tool install mcp-proxy

# Option 2: With pipx (alternative)
pipx install mcp-proxy
```

Once installed, you can run the server using the `mcp-proxy` command.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Projects

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - The official async Python SDK for MCP
- [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy) - A proxy tool to connect Claude Desktop with MCP servers

## License

MIT License

## Testing with MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a useful tool for testing and debugging MCP servers. It provides a web interface to inspect and test MCP server endpoints.

### Installation

Install MCP Inspector using npm:

```bash
npm install -g @modelcontextprotocol/inspector
```

### Usage

1. Start your MCP server (e.g., the Flask example above)
2. Run MCP Inspector:

```bash
git clone git@github.com:modelcontextprotocol/inspector.git
cd inspector
npm run build
npm start
```

3. Open your browser and navigate to `http://127.0.0.1:6274/`
4. Enter your MCP server URL (e.g., `http://localhost:9000/sse`)
5. Use the inspector to:
   - Change transport type to SSE
   - Test server connections
   - Monitor SSE events
   - Send test messages
   - Debug responses

This tool is particularly useful during development to ensure your MCP server implementation
is working correctly and complies with the protocol specification.
