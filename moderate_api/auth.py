import logging
from dataclasses import dataclass
from typing import Union

import jwt
from fastapi import Request

_logger = logging.getLogger(__name__)


@dataclass
class User:
    token_decoded: dict

    def to_dict(self) -> dict:
        return self.token_decoded


async def get_user(request: Request) -> Union[User, None]:
    auth_token = request.headers.get("Authorization")

    if not auth_token:
        return None

    try:
        auth_token = auth_token.replace("Bearer ", "")
        header = jwt.get_unverified_header(auth_token)
        alg = header["alg"]

        token_decoded = jwt.decode(
            auth_token, algorithms=[alg], options={"verify_signature": False}
        )

        return User(token_decoded=token_decoded)
    except Exception:
        _logger.warning("Failed to decode JWT token", exc_info=True)
        return None
