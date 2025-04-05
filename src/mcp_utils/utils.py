"""Utility functions for MCP server implementation."""

from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any, get_type_hints

from pydantic import create_model


@dataclass
class CallableMetadata:
    """Metadata about a callable's signature."""

    arg_model: type[Any]  # Pydantic model for arguments
    return_type: type[Any]  # Return type of the callable


def inspect_callable(
    func: Callable,
    *,
    skip_names: list[str] = None,
) -> CallableMetadata:
    """Inspect a callable and return its type information.

    Args:
        func: The callable to inspect
        skip_names: List of argument names to skip

    Returns:
        CallableMetadata containing arg_model (Pydantic model for args) and return type
    """
    skip_names = skip_names or []
    sig = signature(func)
    type_hints = get_type_hints(func)

    # Build field definitions for the model
    fields: dict[str, tuple[type, Any]] = {}

    for name, param in sig.parameters.items():
        if name in skip_names:
            continue

        # Get the type annotation
        param_type = type_hints.get(name, Any)

        # Determine default value
        if param.default is Parameter.empty:
            fields[name] = (param_type, ...)
        else:
            fields[name] = (param_type, param.default)

    # Create a dynamic model for the arguments
    arg_model = create_model(f"{func.__name__}Args", **fields)

    return CallableMetadata(
        arg_model=arg_model, return_type=type_hints.get("return", Any)
    )
