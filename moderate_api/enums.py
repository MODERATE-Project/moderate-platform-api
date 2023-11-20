import enum


class Tags(enum.Enum):
    """Enumeration of route tags."""

    PUBLIC = "Public"


class Entities(enum.Enum):
    "Enumeration of types of entities or classes in the API."

    ASSET = "asset"


class Actions(enum.Enum):
    """Enumeration of actions that can be performed on entities."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
