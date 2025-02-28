"""
Data models for OpenAPI to MCP conversion.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPParameter(BaseModel):
    """Represents a parameter in the MCP format."""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    default: Optional[Union[str, int, float, bool, List, Dict]] = None


class MCPEndpoint(BaseModel):
    """Represents an endpoint in the MCP format."""

    name: str
    description: Optional[str] = None
    parameters: List[MCPParameter] = Field(default_factory=list)
    returns: Optional[Dict] = None
    examples: Optional[List[Dict]] = None
