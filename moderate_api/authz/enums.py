import enum


class TokenFields(enum.Enum):
    "Enumeration of fields in an OIDC access token."

    REALM_ACCESS = "realm_access"
    RESOURCE_ACCESS = "resource_access"
    ROLES = "roles"
    PREFERRED_USERNAME = "preferred_username"
