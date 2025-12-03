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
    ACCESS_REQUEST = "access_request"
    WORKFLOW_JOB = "workflow_job"


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
    ACCESS_REQUEST = "/request"
    WORKFLOW_JOB = "/job"


class Notebooks(enum.Enum):
    """Enumeration of types of notebooks in the API."""

    EXPLORATION = "exploration"
    SYNTHETIC_LOAD = "synthetic-load"


class WorkflowJobTypes(enum.Enum):
    """Enumeration of types of workflow jobs in the API,
    which also determine the name of the message broker queues."""

    MATRIX_PROFILE = "matrix_profile"


class Tokens(str, enum.Enum):
    """Enumeration of token-related constants."""

    ACCESS_TOKEN_COOKIE = "access_token"
