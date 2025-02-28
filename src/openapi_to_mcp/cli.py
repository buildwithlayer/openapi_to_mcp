"""
Command-line interface for the OpenAPI to MCP converter.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

from .converter import OpenAPItoMCPConverter
from .dereferencer import PathDereferencer, DereferenceError

app = typer.Typer(help="Convert OpenAPI specifications to MCP format")


def _load_yaml(path: Path) -> dict:
    """Load a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        The loaded YAML content

    Raises:
        typer.Exit: If the file cannot be loaded
    """
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        typer.echo(f"Error loading {path}: {str(e)}", err=True)
        raise typer.Exit(1)


def _save_yaml(content: dict, path: Path) -> None:
    """Save content to a YAML file.

    Args:
        content: The content to save
        path: Path where to save the file

    Raises:
        typer.Exit: If the file cannot be saved
    """
    try:
        with open(path, "w") as f:
            yaml.dump(content, f, sort_keys=False)
    except Exception as e:
        typer.echo(f"Error saving to {path}: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Path to the input OpenAPI YAML file"),
    output_file: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to save the output MCP YAML file. If not provided, will use input filename with .mcp.yaml extension",
    ),
) -> None:
    """Convert an OpenAPI specification to MCP format."""
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}.json"

    try:
        converter = OpenAPItoMCPConverter.from_yaml(str(input_file))
        converter.save_mcp(str(output_file))
        typer.echo(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def dereference(
    input_file: Path = typer.Argument(..., help="Path to the input OpenAPI spec"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to save the dereferenced spec. If not provided, will use input filename with .dereferenced.yaml suffix",
    ),
) -> None:
    """Dereference paths in an OpenAPI specification."""
    if not input_file.exists():
        typer.echo(f"Input file not found: {input_file}", err=True)
        raise typer.Exit(1)

    # Default output file is input file with .dereferenced.yaml suffix
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}.dereferenced.yaml"

    # Load input spec
    spec = _load_yaml(input_file)

    try:
        # Create dereferencer with base path as input file's directory
        dereferencer = PathDereferencer(spec, base_path=input_file.parent)
        result = dereferencer.dereference()

        # Save result
        _save_yaml(result, output_file)
        typer.echo(f"Successfully dereferenced {input_file} to {output_file}")

    except DereferenceError as e:
        typer.echo(f"Error dereferencing spec: {str(e)}", err=True)
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()
