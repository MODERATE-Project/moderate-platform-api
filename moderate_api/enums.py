import enum


class Entities(enum.Enum):
    "Enumeration of types of entities or classes in the API."

    ASSET = "asset"


class Actions(enum.Enum):
    """Enumeration of actions that can be performed on entities."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
