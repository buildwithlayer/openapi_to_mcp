# OpenAPI to MCP Tool Format

A tool to convert OpenAPI specifications to MCP Tool Format.  Currently only support `application/json` media type.

```yaml
openapi: 3.0.0
info:
  title: Sample API
  description: Optional multiline or single-line description in [CommonMark](http://commonmark.org/help/) or HTML.
  version: 0.1.9

servers:
  - url: http://api.example.com/v1
    description: Optional server description, e.g. Main (production) server

paths:
  /users:
    post:
      summary: Creates a new user.
      description: Optional extended description in CommonMark or HTML.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                  description: The user's username
                email:
                  type: string
                  format: email
                  description: The user's email address
              required:
                - username
                - email
      responses:
        "201": # status code
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                    format: uuid
                  username:
                    type: string
                  email:
                    type: string
                    format: email
                  createdAt:
                    type: string
                    format: date-time
```

--> 

```json
{
    "name": "POST /users",
    "description": "Creates a new user.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "The user's username"
            },
            "email": {
                "type": "string",
                "format": "email",
                "description": "The user's email address"
            }
        },
        "required": ["username", "email"]       
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "format": "uuid"
            },
            "username": {
                "type": "string"
            },
            "email": {
                "type": "string",
                "format": "email"
            },
            "createdAt": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": ["id", "username", "email", "createdAt"]
    }
}
```