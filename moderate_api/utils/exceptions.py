"""Standard HTTP exception helpers."""

from typing import NoReturn, Optional

from fastapi import HTTPException, status


def raise_not_found(detail: Optional[str] = None) -> NoReturn:
    """Raise a 404 Not Found exception.

    Args:
        detail: Optional detail message for the exception.

    Raises:
        HTTPException: 404 Not Found.
    """
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def raise_forbidden(detail: Optional[str] = None) -> NoReturn:
    """Raise a 403 Forbidden exception.

    Args:
        detail: Optional detail message for the exception.

    Raises:
        HTTPException: 403 Forbidden.
    """
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def raise_service_unavailable(detail: Optional[str] = None) -> NoReturn:
    """Raise a 503 Service Unavailable exception.

    Args:
        detail: Optional detail message for the exception.

    Raises:
        HTTPException: 503 Service Unavailable.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def raise_bad_request(detail: Optional[str] = None) -> NoReturn:
    """Raise a 400 Bad Request exception.

    Args:
        detail: Optional detail message for the exception.

    Raises:
        HTTPException: 400 Bad Request.
    """
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def raise_unauthorized(detail: Optional[str] = None) -> NoReturn:
    """Raise a 401 Unauthorized exception.

    Args:
        detail: Optional detail message for the exception.

    Raises:
        HTTPException: 401 Unauthorized.
    """
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
