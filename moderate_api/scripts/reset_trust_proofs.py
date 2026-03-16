#!/usr/bin/env python3
"""Reset stale IOTA trust proof state so Dagster re-creates proofs.

Clears:
  1. MongoDB: removes ``assets`` subdocuments matching the affected S3 object
     keys from the ``Users`` collection in trust-service's database.
  2. PostgreSQL: sets ``uploaded_s3_object.proof_id = NULL`` so the guard at
     ``trust.py:104`` no longer blocks a fresh ``POST /proof`` call.

Run in dry-run mode first (default), then pass ``--execute`` to apply changes.
"""

import argparse
import asyncio
import logging
import os
import sys
from urllib.parse import quote

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import text

from moderate_api.db import with_session

_logger = logging.getLogger(__name__)

_DEFAULT_MONGO_DATABASE = "moderatetrust"


def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Reset stale IOTA trust proof state in MongoDB and PostgreSQL "
            "so Dagster can re-create fresh proofs automatically."
        )
    )

    parser.add_argument(
        "--asset-keys",
        metavar="KEY",
        nargs="+",
        help=(
            "Limit reset to specific S3 object keys. "
            "Defaults to all objects with a non-null proof_id."
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually perform changes. Default is dry-run (no mutations).",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Skip interactive confirmation (required when stdin is not a TTY).",
    )

    parser.add_argument(
        "--mongo-uri",
        default=None,
        help=(
            "MongoDB connection URI. "
            "If omitted, built from MONGO_INITDB_ROOT_USERNAME, "
            "MONGO_INITDB_ROOT_PASSWORD, and MONGO_ENDPOINT_L or MONGO_ENDPOINT_D."
        ),
    )

    parser.add_argument(
        "--mongo-database",
        default=None,
        help=(
            f"MongoDB database name (default: {_DEFAULT_MONGO_DATABASE}, "
            "env: MONGO_DATABASE)."
        ),
    )

    parser.add_argument(
        "--postgres-url",
        default=None,
        help=(
            "PostgreSQL async URL. "
            "Defaults to the MODERATE_API_POSTGRES_URL env var "
            "or the application get_settings() default."
        ),
    )

    return parser.parse_args()


def _build_mongo_uri(cli_uri: str | None) -> str:
    """Build the MongoDB URI from the CLI arg, MONGO_URI env var, or individual
    credential env vars (MONGO_INITDB_ROOT_USERNAME / PASSWORD / ENDPOINT).

    Args:
        cli_uri: Value of ``--mongo-uri``, or ``None`` to use env vars.

    Returns:
        A fully-formed MongoDB connection URI string.
    """
    if cli_uri:
        return cli_uri

    env_uri = os.environ.get("MONGO_URI")
    if env_uri:
        return env_uri

    username = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "")
    password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "")
    endpoint = os.environ.get("MONGO_ENDPOINT_L") or os.environ.get(
        "MONGO_ENDPOINT_D", "localhost:27017"
    )

    if username and password:
        return f"mongodb://{quote(username, safe='')}:{quote(password, safe='')}@{endpoint}"
    return f"mongodb://{endpoint}"


def _resolve_mongo_database(cli_db: str | None) -> str:
    """Return the MongoDB database name from the CLI arg, MONGO_DATABASE env
    var, or the default constant.

    Args:
        cli_db: Value of ``--mongo-database``, or ``None`` to use env vars.

    Returns:
        Resolved MongoDB database name.
    """
    if cli_db:
        return cli_db
    return os.environ.get("MONGO_DATABASE", _DEFAULT_MONGO_DATABASE)


def _validate_configuration(args: argparse.Namespace) -> tuple[str, str]:
    """Validate args and return (mongo_uri, mongo_database).

    Raises:
        ValueError: If configuration is invalid.
    """
    mongo_uri = _build_mongo_uri(args.mongo_uri)
    mongo_database = _resolve_mongo_database(args.mongo_database)

    _logger.info("MongoDB database: %s", mongo_database)
    _logger.debug("MongoDB URI resolved (credentials redacted from log)")

    if args.postgres_url:
        os.environ["MODERATE_API_POSTGRES_URL"] = args.postgres_url
        _logger.info("PostgreSQL URL overridden via --postgres-url")

    return mongo_uri, mongo_database


async def _discover(
    asset_keys: list[str] | None,
    mongo_uri: str,
    mongo_database: str,
) -> list[dict]:
    """Return list of records: {id, key, proof_id, mongo_count}."""
    records: list[dict] = []

    async with with_session() as session:
        if asset_keys:
            placeholders = ", ".join(f":k{i}" for i in range(len(asset_keys)))
            params = {f"k{i}": k for i, k in enumerate(asset_keys)}
            stmt = text(
                f"SELECT id, key, proof_id FROM uploadeds3object "
                f"WHERE proof_id IS NOT NULL AND key IN ({placeholders})"
            )
        else:
            stmt = text(
                "SELECT id, key, proof_id FROM uploadeds3object "
                "WHERE proof_id IS NOT NULL"
            )
            params = {}

        result = await session.execute(stmt, params)
        rows = result.fetchall()

    _logger.info("PostgreSQL: found %d object(s) with non-null proof_id", len(rows))

    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_uri)
    try:
        collection = client[mongo_database]["Users"]
        for row in rows:
            obj_key = row[1]
            proof_id = row[2]
            count = await collection.count_documents({"assets.assetId": obj_key})
            records.append(
                {
                    "id": row[0],
                    "key": obj_key,
                    "proof_id": proof_id,
                    "mongo_count": count,
                }
            )
    finally:
        client.close()

    return records


def _log_discovery_table(records: list[dict]) -> None:
    """Log discovered records as a formatted table."""
    col_w = max((len(r["key"]) for r in records), default=4)
    col_w = max(col_w, 3)  # minimum width for "Key" header

    _logger.info("  %-*s  %-36s  %10s", col_w, "Key", "proof_id", "mongo_docs")
    _logger.info("  %s", "-" * (col_w + 50))

    for r in records:
        _logger.info(
            "  %-*s  %-36s  %10d",
            col_w,
            r["key"],
            r["proof_id"],
            r["mongo_count"],
        )

    mongo_with_match = sum(1 for r in records if r["mongo_count"] > 0)
    _logger.info(
        "Total rows: %d  |  MongoDB docs with matching subdocument: %d",
        len(records),
        mongo_with_match,
    )


async def _clear_mongo(
    keys: list[str], mongo_uri: str, mongo_database: str
) -> dict[str, int]:
    """Pull asset subdocuments from MongoDB. Returns {key: removed_count}."""
    removed: dict[str, int] = {}
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_uri)
    try:
        collection = client[mongo_database]["Users"]
        for key in keys:
            before = await collection.count_documents({"assets.assetId": key})
            result = await collection.update_many(
                {"assets.assetId": key},
                {"$pull": {"assets": {"assetId": key}}},
            )
            after = await collection.count_documents({"assets.assetId": key})
            removed[key] = before - after
            _logger.info(
                "MongoDB $pull: key=%r matched=%d modified=%d subdocs_removed=%d",
                key,
                result.matched_count,
                result.modified_count,
                removed[key],
            )
    finally:
        client.close()
    return removed


async def _clear_postgres(keys: list[str]) -> int:
    """Set proof_id = NULL for the given keys. Returns count of updated rows."""
    placeholders = ", ".join(f":k{i}" for i in range(len(keys)))
    params = {f"k{i}": k for i, k in enumerate(keys)}
    stmt = text(
        f"UPDATE uploadeds3object SET proof_id = NULL " f"WHERE key IN ({placeholders})"
    )

    async with with_session() as session:
        result = await session.execute(stmt, params)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]


def _confirm_execution(args: argparse.Namespace, record_count: int) -> None:
    """Prompt user for confirmation before executing mutations.

    Raises:
        RuntimeError: If stdin is not a TTY and --yes was not passed.
        SystemExit: If the user declines the prompt.
    """
    if not sys.stdin.isatty():
        if not args.yes:
            raise RuntimeError(
                "stdin is not a TTY. Pass --yes to skip confirmation "
                "in non-interactive mode."
            )
        return

    if args.yes:
        return

    answer = input(
        f"\nAbout to clear proof state for {record_count} object(s). "
        "Continue? [y/N] "
    ).strip()

    if answer.lower() != "y":
        _logger.info("Aborted by user.")
        raise SystemExit(0)


async def _run(args: argparse.Namespace) -> None:
    """Orchestrate the full reset: discover affected objects, confirm with the
    user, then clear MongoDB subdocuments and null out PostgreSQL proof_ids.

    Args:
        args: Parsed command-line arguments from :func:`parse_args`.
    """
    mongo_uri, mongo_database = _validate_configuration(args)

    mode_label = "EXECUTE" if args.execute else "DRY-RUN"
    _logger.info("=== reset-trust-proofs [%s] ===", mode_label)

    # ------------------------------------------------------------------
    # Phase 1 – Discovery
    # ------------------------------------------------------------------
    _logger.info("Phase 1 — Discovery (read-only)...")
    records = await _discover(
        asset_keys=args.asset_keys,
        mongo_uri=mongo_uri,
        mongo_database=mongo_database,
    )

    if not records:
        _logger.info(
            "Nothing to do — no uploaded_s3_object rows with proof_id IS NOT NULL found."
        )
        return

    _log_discovery_table(records)

    if not args.execute:
        _logger.info("Dry-run complete. Pass --execute to apply changes.")
        return

    # ------------------------------------------------------------------
    # Phase 2 – Confirmation gate
    # ------------------------------------------------------------------
    _confirm_execution(args, len(records))

    keys = [r["key"] for r in records]

    # ------------------------------------------------------------------
    # Phase 3 – MongoDB cleanup (before PostgreSQL to avoid race)
    # ------------------------------------------------------------------
    _logger.info("Phase 3 — MongoDB cleanup...")
    removed = await _clear_mongo(keys, mongo_uri, mongo_database)
    total_removed = sum(removed.values())
    _logger.info(
        "MongoDB: removed %d asset subdocument(s) across %d key(s).",
        total_removed,
        len(keys),
    )

    # ------------------------------------------------------------------
    # Phase 4 – PostgreSQL cleanup
    # ------------------------------------------------------------------
    _logger.info("Phase 4 — PostgreSQL cleanup...")
    updated_rows = await _clear_postgres(keys)
    _logger.info("PostgreSQL: updated %d row(s), proof_id set to NULL.", updated_rows)

    # ------------------------------------------------------------------
    # Phase 5 – Summary
    # ------------------------------------------------------------------
    _logger.info(
        "Summary: MongoDB subdocuments removed=%d, PostgreSQL rows updated=%d",
        total_removed,
        updated_rows,
    )
    _logger.info(
        "Dagster sensor polls proof_id=null every 300 s. "
        "New proofs will be created automatically within ~5 minutes."
    )
    _logger.info("Verify with: GET /api/proof/integrity?object_key_or_id=<key>")


def handle_main_error(e: Exception) -> None:
    """Handle errors at the main execution level."""
    _logger.exception("Error during proof reset: %s", str(e))
    _logger.error(
        "Ensure that the PostgreSQL and MongoDB services are reachable "
        "and that connection parameters are correct."
    )


def main() -> None:
    """Main workflow to reset stale trust proof state."""
    setup_logging()
    args = parse_args()

    try:
        asyncio.run(_run(args))
    except SystemExit:
        raise
    except Exception as e:
        handle_main_error(e)
        raise


if __name__ == "__main__":
    setup_logging()
    main()
