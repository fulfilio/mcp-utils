# mcp-utils

A Python utility package for building Model Context Protocol (MCP) servers.

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
def get_weather(city: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(text="sunny")], is_error=False)
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

For a more comprehensive example including logging setup and session management, check out the [example Flask application](https://github.com/fulfilio/mcp-utils/blob/main/examples/flask_app.py) in the repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Related Projects

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - The official async Python SDK for MCP
