import enum


class Tags(enum.Enum):
    """Enumeration of route tags."""

    PUBLIC = "Public"


class Entities(enum.Enum):
    "Enumeration of types of entities or classes in the API."

    ASSET = "asset"
    UPLOADED_OBJECT = "uploaded_object"
    USER = "user"
    VISUALIZATION = "visualization"


class Actions(enum.Enum):
    """Enumeration of actions that can be performed on entities."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class Prefixes(enum.Enum):
    """The prefixes for the different API endpoints."""

    PING = "/ping"
    ASSET = "/asset"
    USER = "/user"
    VISUALIZATION = "/visualization"
    NOTEBOOK = "/notebook"


class Notebooks(enum.Enum):
    """Enumeration of types of notebooks in the API."""

    EXPLORATION = "exploration"
