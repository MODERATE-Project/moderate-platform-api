import dataclasses
import logging
import pprint
from typing import Annotated, Any, TypeVar

import casbin
from fastapi import Depends, HTTPException, Request, status

from moderate_api.authz.enforcer import debug_enforcer, get_enforcer
from moderate_api.authz.enums import TokenFields
from moderate_api.authz.token import get_request_token
from moderate_api.config import Settings, SettingsDep

T = TypeVar("T")

_logger = logging.getLogger(__name__)


@dataclasses.dataclass
class User:
    token_decoded: dict[str, Any]
    _settings: Settings | None = None
    _enforcer: casbin.Enforcer = None

    @property
    def settings(self) -> Settings:
        return self._settings if self._settings else Settings()

    def _extend_enforcer(self, enforcer: casbin.Enforcer) -> casbin.Enforcer:
        _logger.debug("Extending Casbin enforcer with user '%s'", self.username)

        for role in self.roles:
            enforcer.add_role_for_user(self.username, role)

        return enforcer

    @property
    def enforcer(self) -> casbin.Enforcer:
        if self._enforcer:
            return self._enforcer

        enforcer = get_enforcer()
        self._enforcer = self._extend_enforcer(enforcer=enforcer)

        _logger.debug(
            "Effective enforcer for user '%s':\n%s",
            self.username,
            debug_enforcer(enforcer=self._enforcer),
        )

        return self._enforcer

    @property
    def username(self) -> str:
        return self.token_decoded[TokenFields.PREFERRED_USERNAME.value]

    @property
    def roles(self) -> list[str]:
        roles = self.token_decoded.get(TokenFields.REALM_ACCESS.value, {}).get(
            TokenFields.ROLES.value, []
        )

        resource_roles = self.token_decoded.get(TokenFields.RESOURCE_ACCESS.value, {})

        for key, val in resource_roles.items():
            roles.extend([f"{key}:{r}" for r in val.get(TokenFields.ROLES.value, [])])

        return roles

    @property
    def is_enabled(self) -> bool:
        return self.is_admin or self.enforcer.has_role_for_user(
            self.username, self.settings.role_basic_access
        )

    @property
    def is_admin(self) -> bool:
        return self.enforcer.has_role_for_user(self.username, self.settings.role_admin)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token_decoded,
            "is_admin": self.is_admin,
            "roles": self.enforcer.get_implicit_roles_for_user(self.username),
        }

    def enforce_raise(self, obj: str, act: str, admin_bypass: bool = True):
        _logger.debug("Enforcing sub='%s' obj='%s' act='%s'", self.username, obj, act)

        if admin_bypass and self.is_admin:
            _logger.debug("Admin '%s' is allowed to perform any action", self.username)
            return

        if not self.enforcer.enforce(self.username, obj, act):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    def apply_admin_bypass(self, value: T, admin_value: T | None = None) -> T | None:
        """Apply admin bypass logic to a value.

        Returns admin_value if user is admin, otherwise returns value.
        This is useful for conditional logic like user selectors or filters.

        Args:
            value: The value to return for non-admin users.
            admin_value: The value to return for admin users (default: None).

        Returns:
            admin_value if user is admin, otherwise value.

        Example:
            >>> user_selector = user.apply_admin_bypass(selector)
            >>> # Returns None for admins, selector for regular users
        """
        return admin_value if self.is_admin else value

    def get_username_filter(self) -> str | None:
        """Get username filter for queries.

        Returns None for admins (no filter), username for regular users.
        This is useful for filtering queries by username ownership.

        Returns:
            None if user is admin, otherwise the username.

        Example:
            >>> username_filter = user.get_username_filter()
            >>> # Returns None for admins, username for regular users
        """
        return None if self.is_admin else self.username


async def _get_user(request: Request, settings: Settings) -> User:
    token_decoded = await get_request_token(request=request, settings=settings)
    user = User(token_decoded=token_decoded, _settings=settings)

    if not user.is_enabled:
        raise Exception("API access is not enabled for this user")

    return user


async def get_user(request: Request, settings: SettingsDep) -> User:
    """Build a User object from the JWT token in the request.
    Raise an exception if the token is invalid or not present."""

    try:
        return await _get_user(request=request, settings=settings)
    except Exception as ex:
        _logger.debug("Unauthorized request:\n%s", pprint.pformat(dict(request)))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ex)
        ) from ex


UserDep = Annotated[User, Depends(get_user)]


async def get_user_optional(request: Request, settings: SettingsDep) -> User | None:
    """Build a User object from the JWT token in the request.
    Return None if the token is invalid or not present."""

    try:
        return await _get_user(request=request, settings=settings)
    except Exception:
        return None


OptionalUserDep = Annotated[User | None, Depends(get_user_optional)]
