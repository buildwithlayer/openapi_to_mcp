class OpenAPIConverterError(Exception):
    """Base exception for OpenAPI converter errors."""
    pass

class ValidationError(OpenAPIConverterError):
    """Raised when the OpenAPI specification is invalid."""
    pass

class ConversionError(OpenAPIConverterError):
    """Raised when there is an error during the conversion process."""
    pass

class UnsupportedFeatureError(OpenAPIConverterError):
    """Raised when an unsupported OpenAPI feature is encountered."""
    pass
