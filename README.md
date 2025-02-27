# OpenAPI to OpenAI Functions Converter

A Python package that converts OpenAPI 3.0/3.1 specifications into OpenAI function definitions, focusing on endpoint-to-function conversion with structured parameter organization.

## Features

- Supports OpenAPI 3.0 and 3.1 specifications
- Accepts YAML and JSON formats
- Converts API endpoints to OpenAI function definitions
- Organizes parameters by type (path, query, body, auth)
- Validates input specifications
- Provides detailed error messages

## Installation

```bash
pip install openapi-to-openai-functions
```

## Usage

### Basic Usage

```python
from openapi_to_openai_functions import OpenAPIConverter
from pathlib import Path

# Load from a file
converter = OpenAPIConverter(Path("path/to/openapi.yaml"))
functions, json_str = converter.convert()

# Load from a string
yaml_str = """
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
paths:
  /weather/{city}:
    get:
      summary: Get weather information
      parameters:
        - name: city
          in: path
          required: true
          schema:
            type: string
"""
converter = OpenAPIConverter(yaml_str)
functions, json_str = converter.convert()

# Load from a dictionary
spec_dict = {
    "openapi": "3.0.0",
    "info": {"title": "Sample API", "version": "1.0.0"},
    "paths": {...}
}
converter = OpenAPIConverter(spec_dict)
functions, json_str = converter.convert()
```

### Output Format

The converter generates OpenAI function definitions in the following format:

```python
{
    "type": "function",
    "function": {
        "name": "GET_WEATHER_CITY",
        "description": "Get weather information",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string"
                        }
                    }
                },
                "query": {
                    "type": "object",
                    "properties": {}
                },
                "body": {
                    "type": "object",
                    "properties": {}
                },
                "auth": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        "strict": true
    }
}
```

## Error Handling

The package provides several custom exceptions:

- `ValidationError`: Raised when the OpenAPI specification is invalid
- `ConversionError`: Raised when there is an error during the conversion process
- `UnsupportedFeatureError`: Raised when an unsupported OpenAPI feature is encountered

Example:

```python
from openapi_to_openai_functions import OpenAPIConverter, ValidationError

try:
    converter = OpenAPIConverter("invalid spec")
except ValidationError as e:
    print(f"Invalid specification: {e}")
```

## Supported Features

- Path parameters
- Query parameters
- Request body (application/json)
- Basic authentication headers
- API key authentication
- Nested objects and arrays
- Required field handling

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
