"""Pydantic models for MCP (Model Context Protocol) schema."""

import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .utils import inspect_callable

logger = logging.getLogger("mcp_utils")


class Role(str, Enum):
    """Role in the MCP protocol."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Annotations(BaseModel):
    """Annotations for MCP objects."""

    audience: list[Role] | None = Field(
        None,
        description="Describes who the intended customer of this object or data is.",
    )
    priority: float | None = Field(
        None,
        description="Describes how important this data is for operating the server.",
        ge=0,
        le=1,
    )


class Annotated(BaseModel):
    """Base for objects that include optional annotations for the client."""

    annotations: Annotations | None = None


class BlobResourceContents(BaseModel):
    """Contents of a blob resource."""

    blob: str = Field(
        ...,
        json_schema_extra={"format": "byte"},
    )
    mime_type: str | None = Field(None, alias="mimeType")
    uri: str = Field(
        ...,
        json_schema_extra={"format": "uri"},
    )


class ToolArguments(RootModel):
    """Arguments for a tool call."""

    root: dict[str, Any]


class TextContent(BaseModel):
    """Text content in MCP."""

    text: str
    type: str = Field("text")


class ImageContent(BaseModel):
    """Image content in MCP."""

    image: BlobResourceContents
    type: str = Field("image")


class EmbeddedResource(BaseModel):
    """Embedded resource content in MCP."""

    resource: BlobResourceContents
    type: str = Field("embedded-resource")


class CallToolRequest(BaseModel):
    """Request to invoke a tool provided by the server."""

    method: Literal["tools/call"]
    params: dict[str, Any] = Field(...)


class CallToolResult(BaseModel):
    """The server's response to a tool call."""

    _meta: dict[str, Any] | None = None
    content: list[TextContent | ImageContent | EmbeddedResource] = Field(...)
    is_error: bool = Field(False, alias="isError")


class CancelledNotification(BaseModel):
    """Notification for cancelling a previously-issued request."""

    method: Literal["notifications/cancelled"]
    params: dict[str, Any] = Field(...)


class ClientCapabilities(BaseModel):
    """Capabilities a client may support."""

    experimental: dict[str, dict[str, Any]] | None = None
    roots: dict[str, bool] | None = None
    sampling: dict[str, Any] | None = None
    prompts: dict[str, bool] | None = None
    resources: dict[str, bool] | None = None
    tools: dict[str, bool] | None = None
    logging: dict[str, bool] | None = None


class CompleteRequestArgument(BaseModel):
    """Argument information for completion request."""

    name: str
    value: str


class CompleteRequest(BaseModel):
    """Request for completion options."""

    method: Literal["completion/complete"]
    params: dict[str, Any] = Field(...)


class CompletionValues(BaseModel):
    """Completion values response."""

    has_more: bool | None = Field(None, alias="hasMore")
    total: int | None = None
    values: list[str] = Field(..., max_length=100)


class CompleteResult(BaseModel):
    """Response to a completion request."""

    _meta: dict[str, Any] | None = None
    completion: CompletionValues


class ResourceReference(BaseModel):
    """Reference to a resource."""

    type: str = Field("resource")
    id: str


class PromptReference(BaseModel):
    """Reference to a prompt."""

    type: str = Field("prompt")
    id: str


class InitializeRequest(BaseModel):
    """Request to initialize the MCP connection."""

    method: Literal["initialize"]
    params: dict[str, Any] = Field(...)


class ServerInfo(BaseModel):
    """Information about the server."""

    name: str
    version: str


class InitializeResult(BaseModel):
    """Result of initialization request."""

    protocolVersion: str
    capabilities: ClientCapabilities
    serverInfo: ServerInfo


class ListResourcesRequest(BaseModel):
    """Request to list available resources."""

    method: Literal["resources/list"]
    params: dict[str, Any] | None = None


class ResourceInfo(BaseModel):
    """Information about a resource."""

    uri: str
    name: str
    description: str = ""
    mime_type: str | None = None

    @classmethod
    def from_callable(cls, callable: Callable, path: str, name: str) -> "ResourceInfo":
        return cls(
            uri=path,
            name=name,
            description=callable.__doc__ or "",
            mime_type="application/json",
        )


class ListResourcesResult(BaseModel):
    """Result of listing resources."""

    resources: list[ResourceInfo]
    nextCursor: str | None = None


class ResourceTemplateInfo(BaseModel):
    """Information about a resource template.

    https://spec.modelcontextprotocol.io/specification/2024-11-05/server/resources/#resource-templates
    """

    uriTemplate: str
    name: str
    description: str = ""
    mimeType: str = "application/json"

    @classmethod
    def from_callable(
        cls, path: str, callable: Callable, name: str
    ) -> "ResourceTemplateInfo":
        return cls(
            uriTemplate=path,
            name=name,
            description=callable.__doc__ or "",
            mimeType="application/json",
        )


class ListResourceTemplateResult(BaseModel):
    """Result of listing resource templates."""

    resourceTemplates: list[ResourceTemplateInfo]
    nextCursor: str | None = None


class ReadResourceRequest(BaseModel):
    """Request to read a specific resource."""

    method: Literal["resources/read"]
    params: dict[str, Any] = Field(...)


class ReadResourceResult(BaseModel):
    """Result of reading a resource."""

    _meta: dict[str, Any] | None = None
    resource: BlobResourceContents


class ListPromptsRequest(BaseModel):
    """Request to list available prompts."""

    method: Literal["prompts/list"]
    params: dict[str, Any] | None = None


class PromptInfo(BaseModel):
    """Information about a prompt.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/prompts/#listing-prompts
    """

    id: str
    name: str
    description: str | None = None
    arguments: list[dict[str, Any]]

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "PromptInfo":
        """Create a PromptInfo from a callable."""
        metadata = inspect_callable(callable)
        arguments = []
        if metadata.arg_model:
            for field_name, field in metadata.arg_model.model_fields.items():
                arguments.append(
                    {
                        "name": field_name,
                        "description": field.description or "",
                        "required": field.is_required(),
                    }
                )
        return cls(
            id=name, name=name, description=callable.__doc__ or "", arguments=arguments
        )


class ListPromptsResult(BaseModel):
    """Result of listing prompts."""

    prompts: list[PromptInfo]
    nextCursor: str | None = None


class GetPromptRequest(BaseModel):
    """Request to get a specific prompt."""

    method: Literal["prompts/get"]
    params: dict[str, Any] = Field(...)


class Message(BaseModel):
    """Message in MCP."""

    role: Literal["system", "user", "assistant"]
    content: TextContent | ImageContent | EmbeddedResource


class GetPromptResult(BaseModel):
    """Result of getting a prompt."""

    _meta: dict[str, Any] | None = None
    description: str
    messages: list[Message]


class ListToolsRequest(BaseModel):
    """Request to list available tools."""

    method: Literal["tools/list"]
    params: dict[str, Any] | None = None


class ToolInfo(BaseModel):
    """Information about a tool.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/tools/#listing-tools
    """

    name: str
    description: str | None = None
    inputSchema: dict[str, Any] = Field(...)
    arg_model: type[BaseModel] | None = Field(None, exclude=True)

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "ToolInfo":
        """Create a ToolInfo from a callable."""
        metadata = inspect_callable(callable)
        return cls(
            name=name,
            description=callable.__doc__ or "",
            inputSchema=metadata.arg_model.model_json_schema(),
            arg_model=metadata.arg_model,
        )


class ListToolsResult(BaseModel):
    """Result of listing tools."""

    tools: list[ToolInfo]
    nextCursor: str | None = None


class SubscribeRequest(BaseModel):
    """Request to subscribe to a resource."""

    method: Literal["resources/subscribe"]
    params: dict[str, Any] = Field(...)


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe from a resource."""

    method: Literal["resources/unsubscribe"]
    params: dict[str, Any] = Field(...)


class SetLevelRequest(BaseModel):
    """Request to set the level of a resource."""

    method: Literal["resources/setLevel"]
    params: dict[str, Any] = Field(...)


class PingRequest(BaseModel):
    """Request to ping the server."""

    method: Literal["ping"]
    params: dict[str, Any] | None = None


class PingResult(BaseModel):
    """Result of ping request."""

    _meta: dict[str, Any] | None = None


class InitializedNotification(BaseModel):
    """Notification that initialization is complete."""

    method: Literal["notifications/initialized"]
    params: dict[str, Any] | None = None


class ProgressNotification(BaseModel):
    """Notification of progress."""

    method: Literal["notifications/progress"]
    params: dict[str, Any] = Field(...)


class RootsListChangedNotification(BaseModel):
    """Notification that the roots list has changed."""

    method: Literal["notifications/rootsListChanged"]
    params: dict[str, Any] | None = None


class CreateMessageRequest(BaseModel):
    """Request to create a message."""

    method: Literal["messages/create"]
    params: dict[str, Any] = Field(...)


class CreateMessageResult(BaseModel):
    """Result of creating a message."""

    message: dict[str, Any]


class ListRootsRequest(BaseModel):
    """Request to list roots."""

    method: Literal["roots/list"]
    params: dict[str, Any] | None = None


class RootInfo(BaseModel):
    """Information about a root."""

    id: str
    name: str
    description: str | None = None


class ListRootsResult(BaseModel):
    """Result of listing roots."""

    roots: list[RootInfo]
    nextCursor: str | None = None


class ErrorResponse(BaseModel):
    """Error response in MCP."""

    code: int = Field(None, description="Error code must be an integer")
    message: str = Field(None, description="Error message describing what went wrong")
    data: Any | None = Field(None, description="Additional error data if available")


class MCPResponse(BaseModel):
    """Base response model for MCP responses."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC version")
    id: str | int = Field(
        None, description="ID matching the request this response corresponds to"
    )
    result: Any | None = Field(None, description="Result of the request if successful")
    error: ErrorResponse | None = Field(
        None, description="Error details if request failed"
    )

    def is_error(self) -> bool:
        """Check if the response contains an error."""
        return self.error is not None


class Result(BaseModel):
    """Generic result type."""

    _meta: dict[str, Any] | None = None


class MCPRequest(BaseModel):
    """Base request model for MCP requests."""

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC version")
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None
