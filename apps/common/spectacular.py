"""
DRF Spectacular extensions.

Registers the custom CustomerJWTAuthentication so Spectacular can
document Bearer token auth in the OpenAPI schema.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomerJWTAuthExtension(OpenApiAuthenticationExtension):
    target_class = "apps.users.authentication.CustomerJWTAuthentication"
    name = "CustomerJWT"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token issued at login/signup. Pass as: Authorization: Bearer <token>",
        }
