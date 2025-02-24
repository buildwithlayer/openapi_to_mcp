import pytest
from openapi_to_openai_functions import OpenAPIConverter
from openapi_to_openai_functions.exceptions import ValidationError, ConversionError
import json
import requests

def test_basic_validation():
    """Test basic validation of OpenAPI spec."""
    # Invalid spec (missing paths)
    invalid_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        }
    }
    
    with pytest.raises(ValidationError):
        OpenAPIConverter(invalid_spec)

def test_simple_conversion():
    """Test conversion of a simple OpenAPI spec."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/weather/{city}": {
                "get": {
                    "description": "Get weather information",
                    "parameters": [
                        {
                            "name": "city",
                            "in": "path",
                            "required": True,
                            "description": "The city to get weather for",
                            "schema": {
                                "type": "string"
                            }
                        },
                        {
                            "name": "units",
                            "in": "query",
                            "required": False,
                            "description": "The unit system to use",
                            "schema": {
                                "type": "string",
                                "enum": ["metric", "imperial"]
                            }
                        }
                    ]
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "GET_WEATHER_CITY"
    assert function["method"] == "GET"
    assert function["url"] == "/weather/{city}"
    
    print("\nConverted function:")
    print(json.dumps(function, indent=2))

def test_yaml_loading():
    yaml_str = """
    openapi: 3.0.0
    info:
      title: Test API
      version: 1.0.0
    paths:
      /test:
        get:
          summary: Test endpoint
    """

    converter = OpenAPIConverter(yaml_str)
    functions = converter.convert()
    assert len(functions) == 1
    assert functions[0]["name"] == "GET_TEST"

def test_request_body():
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/user": {
                "post": {
                    "description": "Create user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "The user's name"
                                        },
                                        "age": {
                                            "type": "integer",
                                            "description": "The user's age"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "POST_USER"
    assert function["method"] == "POST"
    
    body_schema = function["body_schema"]
    assert body_schema is not None
    assert body_schema["type"] == "object"
    assert "name" in body_schema["properties"]
    assert body_schema["properties"]["name"]["type"] == "string"
    assert body_schema["properties"]["name"]["description"] == "The user's name"
    assert "name" in body_schema["required"]
    
    print("\nConverted function with body schema:")
    print(json.dumps(function, indent=2))

def test_security_schemes():
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "components": {
            "securitySchemes": {
                "api_key": {
                    "type": "apiKey",
                    "name": "X-API-Key",
                    "in": "header",
                    "description": "API key for authentication"
                },
                "custom_header": {
                    "type": "apiKey",
                    "name": "Custom-Auth",
                    "in": "header",
                    "description": "Custom authentication header"
                }
            }
        },
        "paths": {
            "/secure": {
                "get": {
                    "description": "Secure endpoint",
                    "security": [
                        {
                            "api_key": []
                        }
                    ]
                }
            },
            "/multi-auth": {
                "post": {
                    "description": "Multi-auth endpoint",
                    "security": [
                        {
                            "api_key": [],
                            "custom_header": []
                        }
                    ]
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 2
    
    secure_function = next(f for f in functions if f["name"] == "GET_SECURE")
    assert secure_function["auth_schema"] is not None
    assert "X-API-Key" in secure_function["auth_schema"]["properties"]
    assert secure_function["auth_schema"]["properties"]["X-API-Key"]["type"] == "string"
    assert secure_function["auth_schema"]["properties"]["X-API-Key"]["description"] == "API key for authentication"
    assert "X-API-Key" in secure_function["auth_schema"]["required"]
    
    multi_auth_function = next(f for f in functions if f["name"] == "POST_MULTI_AUTH")
    assert multi_auth_function["auth_schema"] is not None
    assert "X-API-Key" in multi_auth_function["auth_schema"]["properties"]
    assert "Custom-Auth" in multi_auth_function["auth_schema"]["properties"]
    assert "X-API-Key" in multi_auth_function["auth_schema"]["required"]
    assert "Custom-Auth" in multi_auth_function["auth_schema"]["required"]
    
    print("\nConverted function with security schemes:")
    print(json.dumps(functions, indent=2))

def test_nullable_types():
    """Test handling of nullable types."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/user": {
                "post": {
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "age": {
                                            "type": "integer",
                                            "nullable": True
                                        },
                                        "email": {
                                            "anyOf": [
                                                {"type": "string", "format": "email"},
                                                {"type": "null"}
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    body_schema = function["body_schema"]
    
    age_schema = body_schema["properties"]["age"]
    assert age_schema["type"] == "integer"
    assert age_schema["nullable"] is True
    
    email_schema = body_schema["properties"]["email"]
    assert email_schema["type"] == "string"
    assert email_schema["format"] == "email"
    assert email_schema["nullable"] is True

def test_schema_references():
    """Test handling of schema references."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"$ref": "#/components/schemas/Role"}
                    },
                    "required": ["name", "role"]
                },
                "Role": {
                    "type": "string",
                    "enum": ["admin", "user"]
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "POST_USERS"
    
    body_schema = function["body_schema"]
    assert body_schema["type"] == "object"
    assert "name" in body_schema["properties"]
    assert body_schema["properties"]["name"]["type"] == "string"
    
    role_schema = body_schema["properties"]["role"]
    assert role_schema["type"] == "string"
    assert "enum" in role_schema
    assert role_schema["enum"] == ["admin", "user"]

def test_invalid_reference():
    """Test handling of invalid schema references."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/NonExistent"}
                            }
                        }
                    }
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    with pytest.raises(ConversionError) as exc_info:
        converter.convert()
    assert "Could not resolve reference" in str(exc_info.value)

def test_circular_references():
    """Test handling of circular references in schemas."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/recursive": {
                "post": {
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Node"}
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "children": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Node"}
                        }
                    }
                },
                "Employee": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "manager": {"$ref": "#/components/schemas/Employee"}
                    }
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "POST_RECURSIVE"
    
    body_schema = function["body_schema"]
    assert body_schema["type"] == "object"
    assert "id" in body_schema["properties"]
    assert body_schema["properties"]["id"]["type"] == "string"
    
    # Check that circular reference is handled
    children_schema = body_schema["properties"]["children"]
    assert children_schema["type"] == "array"
    assert children_schema["items"]["type"] == "object"
    assert "Circular reference to" in children_schema["items"]["description"]
    
    print("\nConverted function with circular references:")
    print(json.dumps(function, indent=2)) 

def test_layer_spec():
    """Test handling of layer spec."""
    # Fetch the OpenAPI spec from Layer's API
    response = requests.get("https://api.buildwithlayer.com/openapi.json")
    spec = response.json()

    converter = OpenAPIConverter(spec)
    functions = converter.convert()

    # Basic validation of converted functions
    assert len(functions) > 0
    
    print("\nConverted Layer API functions:")
    print(f"Total functions converted: {len(functions)}")
    print("\nExample function (chat completion):")
    print(json.dumps(functions, indent=2))

def test_server_url():
    """Test handling of servers property in OpenAPI spec."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "https://api.example.com/v1"
            }
        ],
        "paths": {
            "/test": {
                "get": {
                    "description": "Test endpoint"
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "GET_TEST"
    assert function["url"] == "https://api.example.com/v1/test"
    
    print("\nConverted function with server URL:")
    print(json.dumps(function, indent=2))

def test_summary_fallback():
    """Test using summary as fallback for description."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/test1": {
                "get": {
                    "description": "Test endpoint with description"
                }
            },
            "/test2": {
                "get": {
                    "summary": "Test endpoint with summary only"
                }
            },
            "/test3": {
                "get": {
                    "description": "Test endpoint with both",
                    "summary": "This summary should not be used"
                }
            },
            "/test4": {
                "get": {}
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 4
    
    # Test endpoint with description
    function1 = next(f for f in functions if f["name"] == "GET_TEST1")
    assert function1["description"] == "Test endpoint with description"
    
    # Test endpoint with only summary
    function2 = next(f for f in functions if f["name"] == "GET_TEST2")
    assert function2["description"] == "Test endpoint with summary only"
    
    # Test endpoint with both description and summary (should use description)
    function3 = next(f for f in functions if f["name"] == "GET_TEST3")
    assert function3["description"] == "Test endpoint with both"
    
    # Test endpoint with neither
    function4 = next(f for f in functions if f["name"] == "GET_TEST4")
    assert function4["description"] == ""
    
    print("\nConverted functions with summary fallback:")
    print(json.dumps(functions, indent=2))

def test_nested_references():
    """Test handling of nested schema references."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/order": {
                "post": {
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Order"}
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Order": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "customer": {"$ref": "#/components/schemas/Customer"},
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/OrderItem"}
                        }
                    }
                },
                "Customer": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"$ref": "#/components/schemas/Address"},
                        "preferences": {"$ref": "#/components/schemas/CustomerPreferences"}
                    }
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "country": {"type": "string"}
                    }
                },
                "CustomerPreferences": {
                    "type": "object",
                    "properties": {
                        "newsletter": {"type": "boolean"},
                        "favoriteCategories": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "OrderItem": {
                    "type": "object",
                    "properties": {
                        "product": {"$ref": "#/components/schemas/Product"},
                        "quantity": {"type": "integer"}
                    }
                },
                "Product": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "category": {"$ref": "#/components/schemas/Category"}
                    }
                },
                "Category": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "parent": {"$ref": "#/components/schemas/Category"}  # Circular reference
                    }
                }
            }
        }
    }

    converter = OpenAPIConverter(spec)
    functions = converter.convert()
    assert len(functions) == 1
    
    function = functions[0]
    assert function["name"] == "POST_ORDER"
    
    body_schema = function["body_schema"]
    assert body_schema["type"] == "object"
    assert "customer" in body_schema["properties"]
    
    # Verify nested reference resolution
    customer_schema = body_schema["properties"]["customer"]
    assert customer_schema["type"] == "object"
    assert "address" in customer_schema["properties"]
    
    # Verify deeply nested reference resolution
    address_schema = customer_schema["properties"]["address"]
    assert address_schema["type"] == "object"
    assert "street" in address_schema["properties"]
    
    # Verify array items with nested references
    items_schema = body_schema["properties"]["items"]
    assert items_schema["type"] == "array"
    assert items_schema["items"]["type"] == "object"
    assert "product" in items_schema["items"]["properties"]
    
    # Verify circular reference handling
    product_schema = items_schema["items"]["properties"]["product"]
    category_schema = product_schema["properties"]["category"]
    parent_schema = category_schema["properties"]["parent"]
    assert "Circular reference to" in parent_schema["description"]
    
    print("\nConverted function with nested references:")
    print(json.dumps(function, indent=2))

