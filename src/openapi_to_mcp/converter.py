"""
Core functionality for converting OpenAPI specifications to MCP format.
"""

from typing import Dict, List, Optional
import yaml
from .models import MCPEndpoint, MCPParameter


class OpenAPItoMCPConverter:
    """Converts OpenAPI specifications to MCP format."""

    def __init__(self, openapi_spec: Dict):
        """Initialize the converter with an OpenAPI specification.

        Args:
            openapi_spec: Dictionary containing the OpenAPI specification
        """
        self.spec = openapi_spec
        self.endpoints: List[MCPEndpoint] = []

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "OpenAPItoMCPConverter":
        """Create a converter instance from a YAML file.

        Args:
            yaml_path: Path to the OpenAPI YAML file

        Returns:
            An instance of OpenAPItoMCPConverter
        """
        with open(yaml_path, "r") as f:
            spec = yaml.safe_load(f)
        return cls(spec)

    def convert(self) -> List[MCPEndpoint]:
        """Convert the OpenAPI spec to MCP format.

        Returns:
            List of MCPEndpoint objects
        """
        # TODO: Implement conversion logic
        return self.endpoints

    def save_mcp(self, output_path: str) -> None:
        """Save the converted MCP specification to a YAML file.

        Args:
            output_path: Path where to save the MCP YAML file
        """
        mcp_endpoints = self.convert()
        mcp_dict = {"endpoints": [endpoint.model_dump() for endpoint in mcp_endpoints]}

        with open(output_path, "w") as f:
            yaml.safe_dump(mcp_dict, f, sort_keys=False)
