import contextlib
import importlib.resources
import logging
import pprint
from typing import Annotated

import casbin
from fastapi import Depends

import moderate_api.authz

_CASBIN_CONF_NAME = "casbin_model.conf"
_CASBIN_POLICY_NAME = "casbin_policy_static.csv"

_logger = logging.getLogger(__name__)


def debug_enforcer(enforcer: casbin.Enforcer) -> str:
    result = "## Roles:\n"

    result += pprint.pformat(
        {r: enforcer.get_users_for_role(r) for r in enforcer.get_all_roles()}
    )

    result += "\n\n## Policies:\n"
    result += pprint.pformat(enforcer.get_policy())

    return result


def get_enforcer() -> casbin.Enforcer:
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

    return enforcer


EnforcerDep = Annotated[casbin.Enforcer, Depends(get_enforcer)]
