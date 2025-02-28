"""OpenAPI to MCP converter package."""

from .converter import OpenAPItoMCPConverter
from .models import MCPEndpoint, MCPParameter

__version__ = "0.1.0"
__all__ = ["OpenAPItoMCPConverter", "MCPEndpoint", "MCPParameter"]


def hello() -> str:
    return "Hello from openapi-to-mcp!"
