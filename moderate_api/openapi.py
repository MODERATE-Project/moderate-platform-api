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

    parser.add_argument(
        "--openapi-version", type=str, help="The OpenAPI version to use.", default=None
    )

    args = parser.parse_args()

    openapi_version = args.openapi_version or app.openapi_version
    _logger.info("Generating OpenAPI schema for version %s", openapi_version)

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=openapi_version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
    )

    with open(args.path, "w") as fh:
        _logger.info("Writing OpenAPI schema to: %s", args.path)
        json.dump(openapi_schema, fh, indent=2)
