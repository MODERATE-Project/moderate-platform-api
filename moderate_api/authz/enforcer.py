import contextlib
import importlib.resources
import logging
import pprint

import casbin
from fastapi import Depends
from typing_extensions import Annotated

import moderate_api.authz
from moderate_api.authz import User, UserDep

_CASBIN_CONF_NAME = "casbin_model.conf"
_CASBIN_POLICY_NAME = "casbin_policy_static.csv"

_logger = logging.getLogger(__name__)


def extend_enforcer(enforcer: casbin.Enforcer, user: User) -> casbin.Enforcer:
    for role in user.roles:
        enforcer.add_role_for_user(user.username, role)

    return enforcer


def _debug_enforcer(enforcer: casbin.Enforcer) -> str:
    result = "## Roles:\n"

    result += pprint.pformat(
        {r: enforcer.get_users_for_role(r) for r in enforcer.get_all_roles()}
    )

    result += "\n\n## Policies:\n"
    result += pprint.pformat(enforcer.get_policy())

    return result


async def get_enforcer(user: UserDep) -> casbin.Enforcer:
    with contextlib.ExitStack() as stack:
        model_file = stack.enter_context(
            importlib.resources.path(moderate_api.authz, _CASBIN_CONF_NAME)
        )

        policy_file = stack.enter_context(
            importlib.resources.path(moderate_api.authz, _CASBIN_POLICY_NAME)
        )

        model_path = str(model_file)
        policy_path = str(policy_file)

    _logger.debug(
        "Building Casbin enforcer from model '%s' and policy '%s'",
        model_path,
        policy_path,
    )

    enforcer = casbin.Enforcer(model_path, policy_path)
    _logger.debug("Extending Casbin enforcer with user %s", user.username)
    enforcer = extend_enforcer(enforcer=enforcer, user=user)

    _logger.debug(
        "Resulting configuration after extending enforcer with user '%s':\n%s",
        user.username,
        _debug_enforcer(enforcer=enforcer),
    )

    return enforcer


EnforcerDep = Annotated[casbin.Enforcer, Depends(get_enforcer)]
