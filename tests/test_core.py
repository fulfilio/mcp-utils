"""Tests for MCP core functionality."""

import json
from queue import Empty, Queue
from typing import Any

import pytest

from mcp_utils.core import MCPServer, get_page_of_items
from mcp_utils.queue import ResponseQueueProtocol
from mcp_utils.schema import (
    CallToolResult,
    CompletionValues,
    InitializeResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplateResult,
    ListToolsResult,
    MCPResponse,
    PromptInfo,
    ResourceInfo,
    ResourceTemplateInfo,
    TextContent,
    ToolInfo,
)


class TestResponseQueue(ResponseQueueProtocol):
    """Mock response queue for testing."""

    def __init__(self) -> None:
        self.queues: dict[str, Queue] = {}

    def push_response(self, session_id: str, response: MCPResponse) -> None:
        if session_id not in self.queues:
            self.queues[session_id] = Queue()
        self.queues[session_id].put(response.model_dump_json())

    def wait_for_response(
        self, session_id: str, timeout: float | None = None
    ) -> str | None:
        if session_id not in self.queues:
            return None
        try:
            return self.queues[session_id].get(timeout=timeout)
        except Empty:
            return None

    def clear_session(self, session_id: str) -> None:
        if session_id in self.queues:
            del self.queues[session_id]


@pytest.fixture
def response_queue() -> TestResponseQueue:
    """Create a test response queue."""
    return TestResponseQueue()


@pytest.fixture
def server(response_queue: TestResponseQueue) -> MCPServer:
    """Create a test MCP server."""
    return MCPServer(
        name="Test Server",
        version="1.0.0",
        response_queue=response_queue,
    )


def test_server_initialization(server: MCPServer) -> None:
    """Test server initialization and capabilities."""
    # Test basic attributes
    assert server.name == "Test Server"
    assert server.version == "1.0.0"
    assert server.protocol_version == "2024-11-05"

    # Test capabilities
    capabilities = server.get_capabilities()
    assert isinstance(capabilities, InitializeResult)
    assert capabilities.protocolVersion == server.protocol_version
    assert capabilities.serverInfo.name == server.name
    assert capabilities.serverInfo.version == server.version


def test_session_management(server: MCPServer) -> None:
    """Test session management functionality."""
    # Test session ID generation
    session_id = server.generate_session_id()
    assert isinstance(session_id, str)
    assert len(session_id) > 0

    # Test response queueing
    response = MCPResponse(jsonrpc="2.0", id="1", result={"test": "value"})
    server.queue_response(session_id, response)

    # Test waiting for response
    queued_response = server.wait_for_queued_response(session_id)
    assert queued_response is not None
    response_data = json.loads(queued_response)
    assert response_data["jsonrpc"] == "2.0"
    assert response_data["result"] == {"test": "value"}

    # Test waiting with timeout
    assert server.wait_for_queued_response(session_id, timeout=0.1) is None


def test_tool_registration(server: MCPServer) -> None:
    """Test tool registration."""

    # Test decorator-based registration
    @server.tool()
    def test_tool(arg1: str, arg2: int = 0) -> dict[str, Any]:
        """Test tool docstring."""
        return {"arg1": arg1, "arg2": arg2}

    # Verify tool was registered
    assert "test_tool" in server._tools
    assert "test_tool" in server._tools_list

    # Check tool info
    tool_info = server._tools_list["test_tool"]
    assert isinstance(tool_info, ToolInfo)
    assert tool_info.name == "test_tool"
    assert tool_info.description == "Test tool docstring."

    # Test direct registration
    def another_tool() -> None:
        """Another test tool."""
        pass

    tool_info = ToolInfo(
        name="another",
        description="Another test tool.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )
    server.register_tool("another", another_tool, tool_info)
    assert "another" in server._tools
    assert "another" in server._tools_list


def test_resource_registration(server: MCPServer) -> None:
    """Test resource registration."""

    # Test decorator-based registration
    @server.resource("/test")
    def test_resource() -> dict[str, Any]:
        """Test resource docstring."""
        return {"data": "test"}

    # Verify resource was registered
    assert "/test" in server._resources
    assert "/test" in server._resources_list

    # Check resource info
    resource_info = server._resources_list["/test"]
    assert isinstance(resource_info, ResourceInfo)
    assert resource_info.uri == "/test"
    assert resource_info.description == "Test resource docstring."

    # Test direct registration
    def another_resource() -> None:
        """Another test resource."""
        pass

    resource_info = ResourceInfo(
        uri="/another",
        name="another",
        description="Another test resource.",
    )
    server.register_resource("/another", another_resource, resource_info)
    assert "/another" in server._resources
    assert "/another" in server._resources_list


def test_resource_template_registration(server: MCPServer) -> None:
    """Test resource template registration."""

    # Test decorator-based registration
    @server.resource_template("/test/{id}")
    def test_template(id: str) -> dict[str, Any]:
        """Test template docstring."""
        return {"id": id}

    # Verify template was registered
    assert "/test/{id}" in server._resource_templates
    assert "/test/{id}" in server._resource_template_list

    # Check template info
    template_info = server._resource_template_list["/test/{id}"]
    assert isinstance(template_info, ResourceTemplateInfo)
    assert template_info.uriTemplate == "/test/{id}"
    assert template_info.description == "Test template docstring."


def test_prompt_registration(server: MCPServer) -> None:
    """Test prompt registration and completion handlers."""

    # Test decorator-based registration
    @server.prompt()
    def test_prompt(name: str, count: int = 1) -> list[str]:
        """Test prompt docstring."""
        return [name] * count

    # Add completion handler
    @test_prompt.completion("name")
    def complete_name(value: str) -> list[str]:
        """Complete name parameter."""
        options = ["alice", "bob", "charlie"]
        return [opt for opt in options if opt.startswith(value.lower())]

    # Verify prompt was registered
    assert "test_prompt" in server._prompts
    assert "test_prompt" in server._prompts_list
    assert "name" in server._prompt_completions["test_prompt"]

    # Check prompt info
    prompt_info = server._prompts_list["test_prompt"]
    assert isinstance(prompt_info, PromptInfo)
    assert prompt_info.name == "test_prompt"
    assert prompt_info.description == "Test prompt docstring."

    # Test completion
    completions = server.get_completions("test_prompt", "name", "a")
    assert isinstance(completions, CompletionValues)
    assert "alice" in completions.values


def test_list_operations(server: MCPServer) -> None:
    """Test list operations with pagination."""
    # Register some test items
    for i in range(5):
        # Register a tool
        @server.tool(f"tool_{i}")
        def tool() -> None:
            """Test tool."""
            pass

        # Register a resource
        @server.resource(f"/resource_{i}")
        def resource() -> None:
            """Test resource."""
            pass

        # Register a template
        @server.resource_template(f"/template_{i}/{{id}}")
        def template(id: str) -> None:
            """Test template."""
            pass

        # Register a prompt
        @server.prompt(f"prompt_{i}")
        def prompt() -> None:
            """Test prompt."""
            pass

    # Test listing tools
    tools_result = server.get_list_tools(page=1, page_size=3)
    assert isinstance(tools_result, ListToolsResult)
    assert len(tools_result.tools) == 3
    assert tools_result.nextCursor == "2"

    # Test listing resources
    resources_result = server.get_list_resources(page=1, page_size=3)
    assert isinstance(resources_result, ListResourcesResult)
    assert len(resources_result.resources) == 3
    assert resources_result.nextCursor == "2"

    # Test listing templates
    templates_result = server.get_list_resource_templates(page=1, page_size=3)
    assert isinstance(templates_result, ListResourceTemplateResult)
    assert len(templates_result.resourceTemplates) == 3
    assert templates_result.nextCursor == "2"

    # Test listing prompts
    prompts_result = server.get_list_prompts(page=1, page_size=3)
    assert isinstance(prompts_result, ListPromptsResult)
    assert len(prompts_result.prompts) == 3
    assert prompts_result.nextCursor == "2"

    # Test last page
    tools_result = server.get_list_tools(page=2, page_size=3)
    assert isinstance(tools_result, ListToolsResult)
    assert len(tools_result.tools) == 2
    assert tools_result.nextCursor is None


def test_message_handling(server: MCPServer) -> None:
    """Test message handling."""
    session_id = server.generate_session_id()

    # Test initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "capabilities": {
                "experimental": {},
                "prompts": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "tools": {"listChanged": False},
            },
            "clientInfo": {"name": "Test Client", "version": "1.0.0"},
        },
    }
    server.handle_message(message=init_request, session_id=session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "1"
    assert "result" in response
    assert response["result"]["protocolVersion"] == server.protocol_version

    # Test tool call
    @server.tool()
    def echo(message: str) -> dict[str, str]:
        """Echo the message back."""
        return {"message": message}

    tool_request = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "hello"}},
    }
    server.handle_message(tool_request, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "2"
    assert json.loads(response["result"]["content"][0]["text"]) == {"message": "hello"}

    # Test string return
    @server.tool()
    def echo_str(message: str) -> str:
        """Echo the message back as string."""
        return message

    tool_request = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {"name": "echo_str", "arguments": {"message": "hello"}},
    }
    server.handle_message(tool_request, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "2"
    assert response["result"]["content"][0]["text"] == "hello"

    # Test dict return
    @server.tool()
    def echo_dict(message: str) -> dict:
        """Echo the message back as dict."""
        return {"message": message}

    tool_request = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {"name": "echo_dict", "arguments": {"message": "hello"}},
    }
    server.handle_message(tool_request, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "3"
    assert json.loads(response["result"]["content"][0]["text"]) == {"message": "hello"}

    # Test CallToolResult return
    @server.tool()
    def echo_result(message: str) -> CallToolResult:
        """Echo the message back as CallToolResult."""
        return CallToolResult(content=[TextContent(text=message)])

    tool_request = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {"name": "echo_result", "arguments": {"message": "hello"}},
    }
    server.handle_message(tool_request, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "4"
    assert response["result"]["content"][0]["text"] == "hello"


def test_error_handling(server: MCPServer) -> None:
    """Test error handling."""
    session_id = server.generate_session_id()

    # Test invalid message format
    invalid_message = {"not": "valid"}
    server.handle_message(invalid_message, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["error"]["code"] == -32600  # Invalid Request

    # Test unknown method
    unknown_method = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "unknown",
        "params": {},
    }
    server.handle_message(unknown_method, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["error"]["code"] == -32601  # Method not found

    # Test invalid tool call
    invalid_tool = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
    }
    server.handle_message(invalid_tool, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["error"]["code"] == -32601  # Method not found

    # Test invalid arguments
    @server.tool()
    def test_tool(message: str) -> None:
        """Test tool."""
        pass

    invalid_args = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {"name": "test_tool", "arguments": {"wrong_arg": "value"}},
    }
    server.handle_message(invalid_args, session_id)
    response = json.loads(server.wait_for_queued_response(session_id))
    assert response["error"]["code"] == -32602  # Invalid params


def test_pagination_helper() -> None:
    """Test the get_page_of_items helper function."""
    items = list(range(10))

    # Test first page
    page_items, next_page = get_page_of_items(items, page=1, page_size=3)
    assert page_items == [0, 1, 2]
    assert next_page == "2"

    # Test middle page
    page_items, next_page = get_page_of_items(items, page=2, page_size=3)
    assert page_items == [3, 4, 5]
    assert next_page == "3"

    # Test last page
    page_items, next_page = get_page_of_items(items, page=4, page_size=3)
    assert page_items == [9]
    assert next_page is None

    # Test empty list
    page_items, next_page = get_page_of_items([], page=1, page_size=3)
    assert page_items == []
    assert next_page is None

    # Test invalid page
    page_items, next_page = get_page_of_items(items, page=0, page_size=3)
    assert page_items == []
    assert next_page == "1"
