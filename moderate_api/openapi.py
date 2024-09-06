import argparse
import json
import logging

from fastapi.openapi.utils import get_openapi

from moderate_api.main import app

_logger = logging.getLogger(__name__)


def write_openapi():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema and save to a file."
    )

    parser.add_argument(
        "--path",
        type=str,
        help="The output file path for the OpenAPI schema.",
        default="openapi.json",
    )

    args = parser.parse_args()

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    with open(args.path, "w") as fh:
        _logger.info("Writing OpenAPI schema to %s", args.path)
        json.dump(openapi_schema, fh, indent=2)
