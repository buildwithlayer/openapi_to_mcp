from pathlib import Path
from typing import Union, Tuple, List, Dict, Any, Optional
import yaml
import json
from .exceptions import ValidationError, ConversionError

class OpenAPIConverter:
    def __init__(self, spec: Union[str, dict, Path]):
        """
        Initialize with OpenAPI spec as string, dict, or Path object.

        Args:
            spec: OpenAPI specification as string (JSON/YAML), dictionary, or Path object

        Raises:
            ValidationError: If the specification is invalid
        """
        self.raw_spec = spec
        self.spec = self._load_spec(spec)
        self.validate_spec()
        self.security_schemes = self._load_security_schemes()
        self.components = self.spec.get("components", {})
        self._ref_stack = set()  # Track reference resolution stack

    def _load_security_schemes(self) -> dict:
        """
        Load security schemes from the OpenAPI specification.

        Returns:
            dict: Dictionary of security schemes
        """
        components = self.spec.get("components", {})
        return components.get("securitySchemes", {})

    def _load_spec(self, spec: Union[str, dict, Path]) -> dict:
        """
        Load and parse the OpenAPI specification.

        Args:
            spec: OpenAPI specification as string, dictionary, or Path object

        Returns:
            dict: Parsed OpenAPI specification

        Raises:
            ValidationError: If the specification cannot be parsed
        """
        if isinstance(spec, dict):
            return spec
        
        if isinstance(spec, Path):
            try:
                content = spec.read_text()
            except Exception as e:
                raise ValidationError(f"Failed to read specification file: {e}")
        else:
            content = spec

        try:
            # Try JSON first
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # Try YAML if JSON fails
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValidationError(f"Failed to parse specification: {e}")

    def validate_spec(self) -> bool:
        """
        Validate the OpenAPI specification.

        Returns:
            bool: True if valid

        Raises:
            ValidationError: If the specification is invalid
        """
        if not isinstance(self.spec, dict):
            raise ValidationError("Specification must be a dictionary")

        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in self.spec:
                raise ValidationError(f"Missing required field: {field}")

        version = self.spec["openapi"]
        if not (version.startswith("3.0") or version.startswith("3.1")):
            raise ValidationError(f"Unsupported OpenAPI version: {version}")

        return True

    def _generate_function_name(self, method: str, path: str) -> str:
        """
        Generate a function name from HTTP method and path.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path

        Returns:
            str: Generated function name
        """
        # Remove leading and trailing slashes
        path = path.strip("/")
        # Replace path parameters with underscores
        path = path.replace("{", "").replace("}", "")
        # Replace slashes and hyphens with underscores
        path = path.replace("/", "_").replace("-", "_")
        # Create function name
        return f"{method.upper()}_{path.upper()}"

    def _process_schema(self, schema: dict, path: str = "") -> dict:
        """
        Process a schema, handling references, nullable types, and additional properties.

        Args:
            schema: OpenAPI schema object
            path: Current schema path for circular reference detection

        Returns:
            dict: Processed schema
        """
        if not schema:
            return {}

        # Handle $ref
        if "$ref" in schema:
            ref = schema["$ref"]
            ref_path = f"{path}>{ref}"

            # Check for circular references using the full path
            if ref in self._ref_stack:
                base_type = self._get_base_type_for_ref(ref)
                return {
                    "type": base_type,
                    "description": f"Circular reference to {ref}",
                    "title": ref
                }

            # Try to resolve the schema first
            try:
                resolved_schema = self._resolve_schema_ref(ref)
                # If resolution succeeds, add ref to stack and process
                self._ref_stack.add(ref)
                try:
                    # Process the resolved schema recursively
                    processed = self._process_schema(resolved_schema, ref_path)
                    # Copy over any additional properties from the original schema
                    for key, value in schema.items():
                        if key != "$ref" and key not in processed:
                            processed[key] = value
                    return processed
                finally:
                    self._ref_stack.remove(ref)
            except ConversionError:
                # If resolution fails, return a basic schema
                return {
                    "type": "object",
                    "description": f"Failed to resolve reference: {ref}",
                    "title": ref
                }

        processed = {}

        # Copy basic properties
        for key in ["type", "format", "description", "title", "pattern", "enum", "minimum", "maximum", "minLength", "maxLength"]:
            if key in schema:
                processed[key] = schema[key]

        # Handle nullable
        if schema.get("nullable", False):
            processed["nullable"] = True
        elif "anyOf" in schema and any(s.get("type") == "null" for s in schema["anyOf"]):
            processed["nullable"] = True
            non_null = next(s for s in schema["anyOf"] if s.get("type") != "null")
            for key, value in non_null.items():
                if key not in processed:
                    processed[key] = value

        # Process object properties recursively
        if schema.get("type") == "object" or "properties" in schema:
            processed["type"] = "object"
            if "properties" in schema:
                processed["properties"] = {}
                for prop_name, prop_schema in schema["properties"].items():
                    prop_path = f"{path}>{prop_name}"
                    processed["properties"][prop_name] = self._process_schema(prop_schema, prop_path)
            if "required" in schema:
                processed["required"] = schema["required"]

        # Process array items recursively
        if schema.get("type") == "array" and "items" in schema:
            processed["type"] = "array"
            items_path = f"{path}>items"
            items_schema = schema["items"]
            processed["items"] = self._process_schema(items_schema, items_path)

        # Process allOf, anyOf, oneOf
        for combiner in ["allOf", "anyOf", "oneOf"]:
            if combiner in schema:
                processed[combiner] = [
                    self._process_schema(s, f"{path}>{combiner}[{i}]")
                    for i, s in enumerate(schema[combiner])
                ]

        # Copy any additional properties not handled above
        for key, value in schema.items():
            if key not in processed and key not in ["properties", "items", "allOf", "anyOf", "oneOf"]:
                processed[key] = value

        return processed

    def _resolve_schema_ref(self, ref: str) -> dict:
        """
        Resolve a schema reference.

        Args:
            ref: Reference string (e.g. "#/components/schemas/User")

        Returns:
            dict: Resolved schema

        Raises:
            ConversionError: If reference cannot be resolved
        """
        if not ref.startswith("#/"):
            raise ConversionError(f"Only local references are supported: {ref}")
        
        parts = ref[2:].split("/")
        current = self.spec
        
        for part in parts:
            if part not in current:
                raise ConversionError(f"Could not resolve reference: {ref}")
            current = current[part]
            
        return current

    def _get_base_type_for_ref(self, ref: str) -> str:
        """
        Get the base type for a reference to use in circular reference handling.

        Args:
            ref: Reference string

        Returns:
            str: Base type (object, string, etc.)
        """
        try:
            parts = ref[2:].split("/")
            current = self.spec
            
            # Navigate to the referenced schema
            for part in parts:
                if part not in current:
                    return "object"  # Default to object if can't resolve
                current = current[part]
            
            # Get the base type from the schema
            if isinstance(current, dict):
                if "type" in current:
                    return current["type"]
                if "properties" in current:
                    return "object"
                if "enum" in current:
                    return "string"
            
            return "object"  # Default to object if no type info found
        except:
            return "object"  # Default to object on any error

    def _convert_parameters(self, path_item: dict, method_item: dict) -> tuple[Optional[dict], Optional[dict]]:
        """
        Convert OpenAPI parameters to query and path schemas.

        Args:
            path_item: OpenAPI path item object
            method_item: OpenAPI method item object

        Returns:
            tuple: (query_schema, path_schema), either can be None if empty
        """
        query_schema = {
            "properties": {},
            "additionalProperties": False,
            "required": [],
            "type": "object",
            "isRequired": True
        }
        
        path_schema = {
            "properties": {},
            "additionalProperties": False,
            "required": [],
            "type": "object",
            "isRequired": True
        }

        # Process parameters
        all_params = path_item.get("parameters", []) + method_item.get("parameters", [])
        for param in all_params:
            if "$ref" in param:
                param = self._resolve_schema_ref(param["$ref"])
            
            param_schema = self._process_schema(param.get("schema", {}))
            param_schema["isRequired"] = param.get("required", False)
            param_schema["description"] = param.get("description", "")

            if param["in"] == "path":
                path_schema["properties"][param["name"]] = param_schema
                if param.get("required", False):
                    path_schema["required"].append(param["name"])
            elif param["in"] == "query":
                query_schema["properties"][param["name"]] = param_schema
                if param.get("required", False):
                    query_schema["required"].append(param["name"])

        return (
            query_schema if query_schema["properties"] else None,
            path_schema if path_schema["properties"] else None
        )

    def _convert_request_body(self, method_item: dict) -> Optional[dict]:
        """
        Convert request body to body schema.

        Args:
            method_item: OpenAPI method item object

        Returns:
            Optional[dict]: Body schema or None if no properties
        """
        body_schema = {
            "properties": {},
            "additionalProperties": False,
            "required": [],
            "type": "object",
            "isRequired": False
        }

        if "requestBody" in method_item:
            if "$ref" in method_item["requestBody"]:
                method_item["requestBody"] = self._resolve_schema_ref(method_item["requestBody"]["$ref"])
                
            content = method_item["requestBody"].get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if "$ref" in schema:
                    schema = self._resolve_schema_ref(schema["$ref"])
                processed_schema = self._process_schema(schema)
                body_schema["properties"] = processed_schema.get("properties", {})
                body_schema["required"] = schema.get("required", [])
                body_schema["isRequired"] = method_item["requestBody"].get("required", False)

        return body_schema if body_schema["properties"] else None

    def _process_security_schemes(self, method_item: dict) -> Optional[dict]:
        """
        Process security schemes for the method.

        Args:
            method_item: OpenAPI method item object

        Returns:
            Optional[dict]: Auth schema with header-based security or None if no properties
        """
        auth_schema = {
            "properties": {},
            "additionalProperties": False,
            "required": [],
            "type": "object",
            "isRequired": False
        }

        # Get security requirements for this method
        security_reqs = method_item.get("security", [])
        if not security_reqs and "security" in self.spec:
            # Use global security if no method-specific security
            security_reqs = self.spec["security"]

        for security_req in security_reqs:
            for scheme_name in security_req:
                if scheme_name in self.security_schemes:
                    scheme = self.security_schemes[scheme_name]
                    if scheme.get("in") == "header":
                        auth_schema["properties"][scheme.get("name", scheme_name)] = {
                            "type": "string",
                            "description": scheme.get("description", f"Authentication header for {scheme_name}"),
                            "isRequired": True
                        }
                        auth_schema["required"].append(scheme.get("name", scheme_name))
                        auth_schema["isRequired"] = True

        return auth_schema if auth_schema["properties"] else None

    def convert(self) -> List[dict]:
        """
        Convert OpenAPI spec to OpenAI function definitions.

        Returns:
            List[dict]: List of OpenAI function definitions
        """
        functions = []
        
        # Get base URL from servers if available
        base_url = ""
        if "servers" in self.spec and self.spec["servers"]:
            base_url = self.spec["servers"][0]["url"].rstrip("/")
        
        for path, path_item in self.spec["paths"].items():
            for method, method_item in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                query_schema, path_schema = self._convert_parameters(path_item, method_item)
                body_schema = self._convert_request_body(method_item)
                auth_schema = self._process_security_schemes(method_item)

                # Use summary as fallback for description
                description = method_item.get("description", method_item.get("summary", ""))

                function = {
                    "name": self._generate_function_name(method, path),
                    "url": f"{base_url}{path}",
                    "description": description,
                    "method": method.upper(),
                    "query_schema": query_schema,
                    "path_schema": path_schema,
                    "body_schema": body_schema,
                    "auth_schema": auth_schema,
                    "strict": False
                }
                
                functions.append(function)
        
        return functions
