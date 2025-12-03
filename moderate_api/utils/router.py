import logging
from fastapi import FastAPI

_logger = logging.getLogger(__name__)


def raise_if_trailing_slashes(the_app: FastAPI):
    """Checks the app's routes for trailing slashes and exits if any are found.
    https://github.com/tiangolo/fastapi/discussions/7298#discussioncomment-5135720"""

    for route in the_app.routes:
        if route.path.endswith("/"):
            if route.path == "/":
                continue

            err_msg = (
                "Aborting: paths may not end with a slash. Check route: {}".format(
                    route
                )
            )

            _logger.error(err_msg)
            raise Exception(err_msg)

