from typing import Callable, List, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression

from moderate_api.authz.enforcer import *
from moderate_api.authz.enums import *
from moderate_api.authz.token import *
from moderate_api.authz.user import *
from moderate_api.authz.user import User


class UserSelectorBuilder(Protocol):
    def __call__(self, user: User, session: AsyncSession) -> List[BinaryExpression]:
        ...
