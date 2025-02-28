"""Tests for the OpenAPI path dereferencer."""

import json
import os
import yaml
import pytest
from pathlib import Path
from typing import Dict, Any, Tuple

from openapi_to_mcp.dereferencer import PathDereferencer, DereferenceError


def load_fixture(name: str) -> Tuple[Dict[str, Any], Dict[str, Any], Path]:
    """Load a test fixture.

    Args:
        name: Name of the fixture directory

    Returns:
        Tuple of (input spec, expected output spec, fixture directory path)
    """
    fixture_dir = Path(__file__).parent / "fixtures" / name

    with open(fixture_dir / "input.yaml") as f:
        input_spec = yaml.safe_load(f)

    with open(fixture_dir / "expected.yaml") as f:
        expected_spec = yaml.safe_load(f)

    return input_spec, expected_spec, fixture_dir


def test_petstore_dereferencing():
    """Test dereferencing the petstore spec."""
    input_spec, expected_spec, fixture_dir = load_fixture("petstore")

    dereferencer = PathDereferencer(input_spec, base_path=fixture_dir)
    result = dereferencer.dereference()

    assert result == expected_spec


def test_circular_references():
    """Test handling of circular references."""
    input_spec, expected_spec, fixture_dir = load_fixture("circular")

    dereferencer = PathDereferencer(input_spec)
    result = dereferencer.dereference()

    assert result == expected_spec


def test_invalid_path_ref_error():
    """Test that invalid path references raise appropriate errors."""
    spec = {"paths": {"/invalid": {"$ref": "#/paths/nonexistent"}}}

    dereferencer = PathDereferencer(spec)
    with pytest.raises(DereferenceError):
        dereferencer.dereference()


def test_additional_path_properties_preservation():
    """Test that additional properties alongside path $ref are preserved."""
    spec = {
        "paths": {
            "/base": {"get": {"summary": "Base endpoint"}},
            "/extended": {
                "$ref": "#/paths/~1base",
                "description": "Extended endpoint",
                "servers": [{"url": "https://api.example.com"}],
            },
        }
    }

    dereferencer = PathDereferencer(spec)
    result = dereferencer.dereference()

    extended = result["paths"]["/extended"]
    assert "get" in extended  # From base
    assert extended["description"] == "Extended endpoint"  # Additional property
    assert (
        extended["servers"][0]["url"] == "https://api.example.com"
    )  # Additional property


def test_non_path_content_preserved():
    """Test that non-path content in the spec is preserved."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {"/test": {"get": {"summary": "Test endpoint"}}},
        "components": {"schemas": {"Test": {"type": "object"}}},
    }

    dereferencer = PathDereferencer(spec)
    result = dereferencer.dereference()

    # Check that non-path content is unchanged
    assert result["openapi"] == "3.0.0"
    assert result["info"]["title"] == "Test API"
    assert "components" in result
    assert result["components"]["schemas"]["Test"]["type"] == "object"
