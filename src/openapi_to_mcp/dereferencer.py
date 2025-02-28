"""
Path dereferencer for OpenAPI specifications.

This module handles resolving $ref references in OpenAPI paths, including:
- Local references (e.g. "#/paths/pet")
- File references (e.g. "./common.yaml#/paths/health")
"""

from typing import Any, Dict, Optional, Union, Set
from pathlib import Path
import copy
import json
import os
import urllib.request
import yaml


class DereferenceError(Exception):
    """Raised when a reference cannot be resolved."""

    pass


class PathDereferencer:
    """Resolves references in OpenAPI paths."""

    def __init__(
        self, spec: Dict[str, Any], base_path: Optional[Union[str, Path]] = None
    ):
        """Initialize the path dereferencer.

        Args:
            spec: The OpenAPI specification dictionary
            base_path: Base path for resolving relative file references. If not provided,
                      uses the current working directory.
        """
        self.spec = copy.deepcopy(spec)
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._cache: Dict[str, Any] = {}
        self._ref_stack: Set[str] = set()

    def _resolve_json_pointer(self, obj: Dict[str, Any], pointer: str) -> Any:
        """Resolve a JSON pointer within an object.

        Args:
            obj: The object to traverse
            pointer: JSON pointer (e.g. "/paths/pet")

        Returns:
            The referenced value

        Raises:
            DereferenceError: If the pointer cannot be resolved
        """
        if not pointer.startswith("/"):
            raise DereferenceError(f"Invalid JSON pointer: {pointer}")

        parts = pointer.lstrip("/").split("/")
        current = obj

        for part in parts:
            # Unescape JSON pointer encoding
            part = part.replace("~1", "/").replace("~0", "~")

            try:
                current = current[part]
            except (KeyError, TypeError, IndexError):
                raise DereferenceError(f"Could not resolve pointer {pointer}")

        return current

    def _load_external_ref(self, ref_path: str) -> Any:
        """Load an external reference from file or URL.

        Args:
            ref_path: Path to the external reference

        Returns:
            The loaded reference content

        Raises:
            DereferenceError: If the reference cannot be loaded
        """
        if ref_path in self._cache:
            return self._cache[ref_path]

        try:
            if ref_path.startswith(("http://", "https://")):
                with urllib.request.urlopen(ref_path) as response:
                    content = response.read()
                    if ref_path.endswith(".yaml") or ref_path.endswith(".yml"):
                        data = yaml.safe_load(content)
                    else:
                        data = json.loads(content)
            else:
                # Handle relative file paths
                file_path = self.base_path / ref_path
                with open(file_path) as f:
                    if str(file_path).endswith((".yaml", ".yml")):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)

            self._cache[ref_path] = data
            return data
        except Exception as e:
            raise DereferenceError(
                f"Failed to load external reference {ref_path}: {str(e)}"
            )

    def _resolve_ref(self, ref: str) -> Any:
        """Resolve a $ref string to its value.

        Args:
            ref: The reference string (e.g. "#/paths/pet" or "./common.yaml#/paths/health")

        Returns:
            The dereferenced value

        Raises:
            DereferenceError: If the reference cannot be resolved
        """
        if "#" in ref:
            file_path, pointer = ref.split("#", 1)
        else:
            file_path, pointer = ref, ""

        if file_path:
            obj = self._load_external_ref(file_path)
        else:
            obj = self.spec

        if pointer:
            return self._resolve_json_pointer(obj, pointer)
        return obj

    def _dereference_object(
        self, obj: Dict[str, Any], path: str = ""
    ) -> Dict[str, Any]:
        """Recursively dereference an object and its nested properties.

        Args:
            obj: The object to dereference
            path: The path being processed (for error messages)

        Returns:
            The dereferenced object
        """
        if not isinstance(obj, dict):
            return obj

        if "$ref" in obj:
            ref = obj["$ref"]
            if ref in self._ref_stack:
                return {"$$circular_ref": ref}

            self._ref_stack.add(ref)
            try:
                ref_value = self._resolve_ref(ref)
                # Recursively dereference the referenced value
                ref_value = self._dereference_object(ref_value, path)
                # Preserve any additional properties
                result = {k: v for k, v in obj.items() if k != "$ref"}
                result.update(ref_value)
                return result
            finally:
                self._ref_stack.remove(ref)

        # Recursively dereference nested objects
        result = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                result[key] = self._dereference_object(value, f"{path}/{key}")
            elif isinstance(value, list):
                result[key] = [
                    (
                        self._dereference_object(item, f"{path}/{key}")
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def _dereference_paths(self, paths: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively dereference paths and their operations.

        Args:
            paths: The paths object to dereference

        Returns:
            The dereferenced paths object
        """
        result = {}
        for path, path_item in paths.items():
            result[path] = self._dereference_object(path_item, path)
        return result

    def dereference(self) -> Dict[str, Any]:
        """Dereference all references in the OpenAPI specification.

        Returns:
            The specification with all references dereferenced

        Raises:
            DereferenceError: If any reference cannot be resolved
        """
        self._ref_stack.clear()
        result = copy.deepcopy(self.spec)

        # Dereference paths
        if "paths" in result:
            result["paths"] = self._dereference_paths(result["paths"])

        # Dereference components if present
        if "components" in result:
            result["components"] = self._dereference_object(
                result["components"], "/components"
            )

        return result
