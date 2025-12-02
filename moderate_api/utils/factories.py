"""Standard factory functions for SQLModel fields."""

import uuid
from datetime import datetime, timezone


def uuid_factory() -> str:
    """Standard UUID factory for SQLModel fields.

    Returns:
        A string representation of a UUID4.
    """
    return str(uuid.uuid4())


def now_factory() -> datetime:
    """Standard UTC datetime factory for SQLModel fields.

    Returns:
        Current UTC datetime without timezone info (naive datetime).
    """
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)
