#!/usr/bin/env python3
"""
Development fixtures generator for MODERATE platform.

Creates assets and asset objects in the catalogue for development purposes.
Uses the API endpoints with authentication via Keycloak.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import uuid
from io import BytesIO, StringIO
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import pandas as pd
from dotenv import load_dotenv

from moderate_api.entities.asset.models import AssetCreate

_logger = logging.getLogger(__name__)


def load_env_files():
    """Load environment variables from .env.dev and .env.dev.default files."""
    script_dir = Path(__file__).parent.parent
    env_dev = script_dir / ".env.dev"
    env_dev_default = script_dir / ".env.dev.default"

    # Load .env.dev.default first (defaults), then .env.dev (overrides)
    if env_dev_default.exists():
        load_dotenv(env_dev_default, override=False)
        _logger.debug("Loaded environment from: %s", env_dev_default)

    if env_dev.exists():
        load_dotenv(env_dev, override=True)
        _logger.debug("Loaded environment from: %s", env_dev)
    else:
        _logger.debug("No .env.dev file found, using defaults from .env.dev.default")


def get_keycloak_token(
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    """Obtain an access token from Keycloak using password grant.

    Args:
        keycloak_url: Base URL of Keycloak (e.g., http://localhost:8989)
        realm: Realm name (e.g., 'moderate')
        client_id: OAuth client ID (e.g., 'apisix')
        client_secret: OAuth client secret
        username: Username for password grant
        password: Password for password grant

    Returns:
        Access token string

    Raises:
        httpx.HTTPStatusError: If token request fails
    """
    token_endpoint = (
        f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
    )

    _logger.debug("Requesting token from Keycloak: %s", token_endpoint)

    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            token_endpoint,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
                "scope": "openid profile email",
            },
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("No access_token in Keycloak response")

        _logger.debug("Successfully obtained token from Keycloak")
        return access_token


def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def generate_csv_file(
    num_rows: Optional[int] = None, num_cols: Optional[int] = None
) -> Tuple[BytesIO, str]:
    """Generate a CSV file with random data.

    Returns:
        Tuple of (BytesIO buffer, filename)
    """
    num_rows = num_rows or random.randint(200, 400)
    num_cols = num_cols or random.randint(10, 20)

    _logger.debug("Generating CSV file with %d rows and %d columns", num_rows, num_cols)

    # Use StringIO for CSV writing (text-based), then convert to BytesIO
    text_buffer = StringIO()
    fieldnames = [f"col_{i}" for i in range(num_cols)]
    writer = csv.DictWriter(text_buffer, fieldnames=fieldnames)
    writer.writeheader()

    for _ in range(num_rows):
        writer.writerow({name: str(uuid.uuid4()) for name in fieldnames})

    # Convert text buffer to bytes
    csv_content = text_buffer.getvalue()
    text_buffer.close()
    buffer = BytesIO(csv_content.encode("utf-8"))

    filename = f"dataset-{uuid.uuid4()}.csv"
    _logger.debug("Generated CSV file: %s", filename)
    return buffer, filename


def generate_json_file(num_records: Optional[int] = None) -> Tuple[BytesIO, str]:
    """Generate a JSON file with nested random data.

    Returns:
        Tuple of (BytesIO buffer, filename)
    """
    num_records = num_records or random.randint(50, 200)

    _logger.debug("Generating JSON file with %d records", num_records)

    data = []
    for _ in range(num_records):
        record = {
            "id": str(uuid.uuid4()),
            "name": f"Item {random.randint(1, 1000)}",
            "value": random.randint(0, 10000),
            "metadata": {
                "category": random.choice(["A", "B", "C", "D"]),
                "tags": [f"tag_{i}" for i in range(random.randint(1, 5))],
                "score": round(random.uniform(0.0, 100.0), 2),
            },
            "timestamp": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:00:00Z",
        }
        data.append(record)

    json_str = json.dumps(data, indent=2)
    buffer = BytesIO(json_str.encode("utf-8"))
    filename = f"dataset-{uuid.uuid4()}.json"
    _logger.debug("Generated JSON file: %s", filename)
    return buffer, filename


def generate_parquet_file(
    num_rows: Optional[int] = None, num_cols: Optional[int] = None
) -> Tuple[BytesIO, str]:
    """Generate a Parquet file with random data using pandas.

    Returns:
        Tuple of (BytesIO buffer, filename)
    """
    num_rows = num_rows or random.randint(200, 400)
    num_cols = num_cols or random.randint(10, 20)

    _logger.debug(
        "Generating Parquet file with %d rows and %d columns", num_rows, num_cols
    )

    # Generate random data
    data = {}
    for i in range(num_cols):
        col_name = f"col_{i}"
        # Mix of data types
        if i % 3 == 0:
            data[col_name] = [random.randint(0, 1000) for _ in range(num_rows)]
        elif i % 3 == 1:
            data[col_name] = [
                round(random.uniform(0.0, 100.0), 2) for _ in range(num_rows)
            ]
        else:
            data[col_name] = [str(uuid.uuid4()) for _ in range(num_rows)]

    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    filename = f"dataset-{uuid.uuid4()}.parquet"
    _logger.debug("Generated Parquet file: %s", filename)
    return buffer, filename


def create_asset_via_api(
    client: httpx.Client,
    base_url: str,
    token: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create an asset via the API."""
    _logger.debug("Creating asset: name=%s", name)
    asset_data = AssetCreate(name=name, description=description)

    # Use .json() and parse it to get a properly serialized dict
    # This handles datetime and enum serialization correctly
    payload = json.loads(asset_data.json(exclude={"created_at"}))

    response = client.post(
        f"{base_url}/asset",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    response.raise_for_status()
    result = response.json()
    _logger.debug(
        "Asset created successfully: id=%s, uuid=%s",
        result.get("id"),
        result.get("uuid"),
    )
    return result


def upload_object_via_api(
    client: httpx.Client,
    base_url: str,
    token: str,
    asset_id: int,
    file_buffer: BytesIO,
    filename: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[dict] = None,
) -> dict:
    """Upload an object to an asset via the API."""
    _logger.debug("Uploading object: asset_id=%s, filename=%s", asset_id, filename)

    # Read file content (ensure we're at the start of the buffer)
    file_buffer.seek(0)
    file_content = file_buffer.read()

    # Prepare multipart form data
    files = {"obj": (filename, file_content, "application/octet-stream")}
    data = {}

    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if tags:
        data["tags"] = json.dumps(tags)

    response = client.post(
        f"{base_url}/asset/{asset_id}/object",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
    )

    response.raise_for_status()
    result = response.json()
    _logger.debug(
        "Object uploaded successfully: id=%s, key=%s",
        result.get("id"),
        result.get("key"),
    )
    return result


def generate_random_asset_name() -> str:
    """Generate a random asset name with varied, natural patterns."""
    # Define multiple naming patterns for variety
    patterns = [
        # Pattern 1: Time period + Topic + Type
        lambda: _pattern_time_topic_type(),
        # Pattern 2: Topic + Purpose/Action
        lambda: _pattern_topic_purpose(),
        # Pattern 3: Source/Origin + Type
        lambda: _pattern_source_type(),
        # Pattern 4: Geographic + Topic
        lambda: _pattern_geographic_topic(),
        # Pattern 5: Product/Service + Metrics
        lambda: _pattern_product_metrics(),
        # Pattern 6: Department + Focus
        lambda: _pattern_department_focus(),
    ]

    return random.choice(patterns)()


def _pattern_time_topic_type() -> str:
    """Generate name like 'Q4 2024 Sales Report' or 'January Customer Data'."""
    time_periods = [
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "2023",
        "2024",
        "2025",
        "H1",
        "H2",
    ]
    topics = [
        "Sales",
        "Revenue",
        "Customer",
        "Marketing",
        "Product",
        "User",
        "Transaction",
        "Order",
        "Payment",
        "Subscription",
        "Engagement",
        "Retention",
        "Churn",
        "Conversion",
        "Traffic",
    ]
    types = [
        "Report",
        "Data",
        "Metrics",
        "Analysis",
        "Dashboard",
        "Records",
        "Transactions",
        "Events",
        "Logs",
    ]

    if random.random() < 0.5:
        # "Q4 2024 Sales Report"
        return f"{random.choice(time_periods)} {random.choice(['', random.choice(['2023', '2024', '2025']) + ' '])}{random.choice(topics)} {random.choice(types)}"
    else:
        # "January Customer Data"
        return f"{random.choice(time_periods)} {random.choice(topics)} {random.choice(types)}"


def _pattern_topic_purpose() -> str:
    """Generate name like 'Customer Segmentation Analysis' or 'Revenue Forecasting'."""
    topics = [
        "Customer",
        "Product",
        "Sales",
        "Marketing",
        "Revenue",
        "User",
        "Order",
        "Inventory",
        "Supply Chain",
        "Pricing",
        "Campaign",
        "Website",
        "Mobile App",
        "Email",
    ]
    purposes = [
        "Segmentation",
        "Forecasting",
        "Analysis",
        "Optimization",
        "Performance",
        "Trends",
        "Insights",
        "Behavior",
        "Satisfaction",
        "Retention",
        "Acquisition",
        "Engagement",
        "Conversion",
        "Churn",
        "Lifetime Value",
    ]

    if random.random() < 0.6:
        # "Customer Segmentation Analysis"
        return f"{random.choice(topics)} {random.choice(purposes)} {random.choice(['Analysis', 'Report', 'Data', 'Metrics'])}"
    else:
        # "Revenue Forecasting"
        return f"{random.choice(topics)} {random.choice(purposes)}"


def _pattern_source_type() -> str:
    """Generate name like 'E-commerce Transaction Records' or 'CRM Customer Data'."""
    sources = [
        "E-commerce",
        "CRM",
        "ERP",
        "POS",
        "Mobile App",
        "Website",
        "Email Campaign",
        "Social Media",
        "Analytics",
        "Customer Support",
        "Salesforce",
        "Marketing Automation",
        "Payment Gateway",
        "Inventory System",
        "Shipping",
    ]
    types = [
        "Transaction Records",
        "Customer Data",
        "Event Logs",
        "Metrics",
        "Analytics Data",
        "Export",
        "Snapshot",
        "Daily Feed",
        "Monthly Summary",
        "Raw Data",
    ]

    return f"{random.choice(sources)} {random.choice(types)}"


def _pattern_geographic_topic() -> str:
    """Generate name like 'European Market Trends' or 'North America Sales Data'."""
    regions = [
        "European",
        "North American",
        "Asian",
        "Global",
        "EMEA",
        "APAC",
        "Americas",
        "Regional",
        "US",
        "UK",
        "German",
        "French",
        "Spanish",
    ]
    topics = [
        "Market Trends",
        "Sales Data",
        "Customer Base",
        "Revenue Metrics",
        "Market Analysis",
        "Performance",
        "Distribution",
        "Operations",
    ]

    return f"{random.choice(regions)} {random.choice(topics)}"


def _pattern_product_metrics() -> str:
    """Generate name like 'Product Performance Dashboard' or 'Service Usage Analytics'."""
    products = [
        "Product",
        "Service",
        "Feature",
        "Platform",
        "Application",
        "System",
        "Solution",
    ]
    metrics = [
        "Performance",
        "Usage",
        "Adoption",
        "Engagement",
        "Health",
        "Quality",
        "Satisfaction",
        "Metrics",
        "Analytics",
        "Monitoring",
        "KPIs",
    ]

    return f"{random.choice(products)} {random.choice(metrics)} {random.choice(['Dashboard', 'Report', 'Data', ''])}".strip()


def _pattern_department_focus() -> str:
    """Generate name like 'Finance Budget Analysis' or 'HR Employee Data'."""
    departments = [
        "Finance",
        "HR",
        "Operations",
        "IT",
        "Legal",
        "Procurement",
        "Logistics",
        "Customer Success",
    ]
    focuses = [
        "Budget",
        "Employee",
        "Vendor",
        "Contract",
        "Asset",
        "Expense",
        "Invoice",
        "Purchase Order",
        "Performance Review",
        "Training",
        "Compliance",
    ]

    return f"{random.choice(departments)} {random.choice(focuses)} {random.choice(['Data', 'Report', 'Analysis', 'Records'])}"


def generate_random_description() -> str:
    """Generate a random description."""
    templates = [
        "A comprehensive dataset containing {type} information.",
        "This dataset provides insights into {type} patterns and trends.",
        "Collection of {type} data for analysis and reporting purposes.",
        "Structured {type} dataset suitable for data science workflows.",
    ]
    types = ["business", "customer", "financial", "operational", "marketing", "sales"]
    return random.choice(templates).format(type=random.choice(types))


def generate_object_name(
    asset_name: str, format_name: str, obj_idx: int, total_objects: int
) -> str:
    """Generate a natural, descriptive object name related to the asset.

    Args:
        asset_name: Name of the parent asset
        format_name: File format (csv, json, parquet)
        obj_idx: Zero-based index of this object
        total_objects: Total number of objects in the asset

    Returns:
        Natural object name
    """
    asset_lower = asset_name.lower()

    # Find year if present
    year_match = re.search(r"202[0-9]", asset_name)
    year = year_match.group(0) if year_match else ""

    # -------------------------------------------------------------------------
    # Strategy 1: Time-based decomposition (Quarters -> Months)
    # -------------------------------------------------------------------------
    quarters = {
        "q1": ["January", "February", "March"],
        "q2": ["April", "May", "June"],
        "q3": ["July", "August", "September"],
        "q4": ["October", "November", "December"],
    }

    for q, months in quarters.items():
        if q in asset_lower:
            # If we have 3 or fewer objects, use distinct months
            if total_objects <= 3:
                month = months[obj_idx % 3]
                base = f"{month}"
                if year:
                    base += f" {year}"

                # Add context from asset name
                context = "Data"
                for term in ["sales", "revenue", "orders", "traffic", "churn", "users"]:
                    if term in asset_lower:
                        context = term.title()
                        break

                return f"{base} {context}"

            # If more objects, use Month + Week or similar
            elif total_objects <= 12:
                month = months[(obj_idx // 4) % 3]
                week = (obj_idx % 4) + 1
                return f"{month} {year if year else ''} - Week {week}"

    # -------------------------------------------------------------------------
    # Strategy 2: Regional decomposition
    # -------------------------------------------------------------------------
    if "european" in asset_lower or "emea" in asset_lower:
        countries = [
            "Germany",
            "France",
            "UK",
            "Italy",
            "Spain",
            "Netherlands",
            "Sweden",
            "Poland",
        ]
        country = countries[obj_idx % len(countries)]

        # Find the topic
        topic = "Data"
        if "market" in asset_lower:
            topic = "Market Data"
        elif "sales" in asset_lower:
            topic = "Sales Records"
        elif "trends" in asset_lower:
            topic = "Trend Analysis"

        return f"{country} {topic}"

    if "north american" in asset_lower or "us " in asset_lower:
        regions = ["Northeast", "Midwest", "South", "West", "Pacific"]
        region = regions[obj_idx % len(regions)]
        return f"{region} Region Data"

    # -------------------------------------------------------------------------
    # Strategy 3: Functional/Topic decomposition
    # -------------------------------------------------------------------------
    if "customer" in asset_lower:
        segments = [
            "Demographics",
            "Purchase History",
            "Web Activity",
            "Support Tickets",
            "Survey Responses",
        ]
        segment = segments[obj_idx % len(segments)]
        return f"Customer {segment}"

    if "product" in asset_lower:
        categories = ["Electronics", "Home & Garden", "Apparel", "Sports", "Toys"]
        category = categories[obj_idx % len(categories)]
        return f"{category} Product Data"

    if "inventory" in asset_lower:
        locs = ["Warehouse A", "Warehouse B", "Distribution Center", "Retail Stores"]
        loc = locs[obj_idx % len(locs)]
        return f"{loc} Inventory"

    if "marketing" in asset_lower or "campaign" in asset_lower:
        channels = ["Email", "Social Media", "Search Ads", "Display Ads", "Affiliates"]
        channel = channels[obj_idx % len(channels)]
        return f"{channel} Campaign Metrics"

    # -------------------------------------------------------------------------
    # Strategy 4: Generic/Fallback (Enhanced)
    # -------------------------------------------------------------------------
    # Extract key noun
    noun = "Data"
    for n in ["transaction", "report", "analysis", "metrics", "logs", "records"]:
        if n in asset_lower:
            noun = n.title()
            break

    # If year is present but no quarter, maybe split by Quarter or Month?
    if year and "q" not in asset_lower:
        if total_objects == 4:
            return f"Q{obj_idx + 1} {year} {noun}"
        if total_objects == 12:
            all_months = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            return f"{all_months[obj_idx % 12]} {year} {noun}"

    # Generic numbered/batched
    prefixes = ["Raw", "Processed", "Aggregated", "Filtered"]
    # Only use prefixes if we have enough objects to cycle through or it makes sense
    if total_objects <= 4 and total_objects > 1:
        # Try to give them distinct processing stages if generic
        if random.random() < 0.5:
            return f"{prefixes[obj_idx % len(prefixes)]} {noun}"

    # Final fallback
    return f"{noun} - Batch {obj_idx + 1:02d}"


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create development fixtures for assets and asset objects"
    )
    parser.add_argument(
        "--num-assets",
        type=int,
        default=10,
        help="Number of assets to create (default: 10)",
    )
    parser.add_argument(
        "--objects-per-asset",
        type=int,
        default=2,
        help="Number of objects per asset (default: 2)",
    )
    parser.add_argument(
        "--keycloak-url",
        type=str,
        default=os.getenv(
            "KEYCLOAK_URL", f"http://localhost:{os.getenv('DEV_KEYCLOAK_PORT', '8989')}"
        ),
        help="Base URL of Keycloak (default: http://localhost:8989 or KEYCLOAK_URL env var)",
    )
    parser.add_argument(
        "--keycloak-realm",
        type=str,
        default=os.getenv("MODERATE_REALM", "moderate"),
        help="Keycloak realm name (default: moderate, or MODERATE_REALM env var)",
    )
    parser.add_argument(
        "--keycloak-client-id",
        type=str,
        default=os.getenv("APISIX_CLIENT_ID", "apisix"),
        help="OAuth client ID (default: apisix, or APISIX_CLIENT_ID env var)",
    )
    parser.add_argument(
        "--keycloak-client-secret",
        type=str,
        default=os.getenv("APISIX_CLIENT_SECRET", "apisix"),
        help="OAuth client secret (default: apisix, or APISIX_CLIENT_SECRET env var)",
    )
    parser.add_argument(
        "--keycloak-username",
        type=str,
        default=os.getenv("KEYCLOAK_USERNAME"),
        help="Keycloak username for authentication (required, or set KEYCLOAK_USERNAME env var)",
    )
    parser.add_argument(
        "--keycloak-password",
        type=str,
        default=os.getenv("KEYCLOAK_PASSWORD"),
        help="Keycloak password for authentication (required, or set KEYCLOAK_PASSWORD env var)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=os.getenv("MODERATE_API_URL", "http://localhost:8000"),
        help="Base URL of the API (default: http://localhost:8000, or MODERATE_API_URL env var)",
    )
    return parser.parse_args()


def validate_configuration(args) -> str:
    """Validate configuration.

    Returns:
        Normalized API URL

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate Keycloak credentials
    if not args.keycloak_username:
        _logger.error(
            "Keycloak username is required. Set --keycloak-username or KEYCLOAK_USERNAME environment variable."
        )
        raise ValueError("Keycloak username is required")

    if not args.keycloak_password:
        _logger.error(
            "Keycloak password is required. Set --keycloak-password or KEYCLOAK_PASSWORD environment variable."
        )
        raise ValueError("Keycloak password is required")

    # Normalize API URL
    api_url = args.api_url.rstrip("/")
    _logger.info("Using API URL: %s", api_url)

    return api_url


def authenticate_with_keycloak(args) -> str:
    """Authenticate with Keycloak and return access token.

    Returns:
        Access token string

    Raises:
        httpx.HTTPStatusError: If authentication fails
        httpx.ConnectError: If connection to Keycloak fails
    """
    _logger.info(
        "Starting fixture generation: assets=%d, objects_per_asset=%d, keycloak_user=%s",
        args.num_assets,
        args.objects_per_asset,
        args.keycloak_username,
    )

    try:
        token = get_keycloak_token(
            keycloak_url=args.keycloak_url,
            realm=args.keycloak_realm,
            client_id=args.keycloak_client_id,
            client_secret=args.keycloak_client_secret,
            username=args.keycloak_username,
            password=args.keycloak_password,
        )
        _logger.info(
            "Successfully authenticated with Keycloak as user: %s",
            args.keycloak_username,
        )
        return token
    except httpx.HTTPStatusError as e:
        _logger.error(
            "Failed to authenticate with Keycloak (status=%d): %s",
            e.response.status_code,
            e.response.text,
        )
        _logger.error(
            "Troubleshooting:\n"
            "  1. Ensure Keycloak is running: docker ps | grep keycloak\n"
            "  2. Verify Keycloak URL: %s\n"
            "  3. Check username/password are correct\n"
            "  4. Ensure the user exists in Keycloak realm '%s'\n"
            "  5. Verify client '%s' supports password grant",
            args.keycloak_url,
            args.keycloak_realm,
            args.keycloak_client_id,
        )
        raise
    except httpx.ConnectError as e:
        _logger.error(
            "Failed to connect to Keycloak at %s: %s",
            args.keycloak_url,
            str(e),
        )
        _logger.error(
            "Troubleshooting:\n"
            "  1. Ensure Keycloak is running: docker ps | grep keycloak\n"
            "  2. Start Keycloak: task dev-up (or docker-compose up -d keycloak)\n"
            "  3. Verify Keycloak URL: %s\n"
            "  4. Check if Keycloak is accessible: curl %s/realms/%s/.well-known/openid-configuration",
            args.keycloak_url,
            args.keycloak_url,
            args.keycloak_realm,
        )
        raise
    except Exception as e:
        _logger.error("Failed to authenticate with Keycloak: %s", str(e), exc_info=True)
        raise


def handle_upload_error(e: Exception, filename: str, asset_id: int) -> bool:
    """Handle errors during object upload.

    Args:
        e: The exception that occurred
        filename: Name of the file being uploaded
        asset_id: ID of the asset

    Returns:
        True if the error was handled and execution should continue, False otherwise
    """
    error_msg = str(e)

    # Log the error - the API handles all storage operations, so we just report HTTP errors
    _logger.error(
        "Failed to upload object via API: filename=%s, asset_id=%s, error=%s",
        filename,
        asset_id,
        error_msg,
        exc_info=True,
    )
    _logger.error(
        "The API server handles all object storage operations. "
        "Check that the API server is running and has proper S3/MinIO/GCS configuration."
    )
    return False


def create_asset_with_objects(
    client: httpx.Client,
    api_url: str,
    token: str,
    asset_idx: int,
    num_assets: int,
    objects_per_asset: int,
) -> Tuple[List[dict], List[dict]]:
    """Create a single asset with its objects.

    Returns:
        Tuple of (created_assets, created_objects) lists
    """
    created_assets = []
    created_objects = []

    # Generate asset metadata
    asset_name = generate_random_asset_name()
    asset_description = generate_random_description()

    _logger.info(
        "Creating asset %d/%d: name=%s",
        asset_idx + 1,
        num_assets,
        asset_name,
    )

    # Create asset
    asset = create_asset_via_api(
        client=client,
        base_url=api_url,
        token=token,
        name=asset_name,
        description=asset_description,
    )
    created_assets.append(asset)

    # Format generators
    format_generators = [
        ("csv", generate_csv_file),
        ("json", generate_json_file),
        ("parquet", generate_parquet_file),
    ]

    # Create objects for this asset
    for obj_idx in range(objects_per_asset):
        # Randomly select format
        format_name, generator_func = random.choice(format_generators)

        _logger.debug(
            "Creating object %d/%d (format=%s) for asset_id=%s",
            obj_idx + 1,
            objects_per_asset,
            format_name,
            asset["id"],
        )

        # Generate file
        file_buffer = None
        try:
            file_buffer, filename = generator_func()

            # Generate metadata
            object_name = generate_object_name(
                asset_name=asset_name,
                format_name=format_name,
                obj_idx=obj_idx,
                total_objects=objects_per_asset,
            )
            object_description = (
                f"{format_name.upper()} dataset containing {format_name} data"
            )
            tags = {
                "format": format_name,
                "generated": "dev-fixtures",
                "index": obj_idx,
            }

            # Upload object
            try:
                obj = upload_object_via_api(
                    client=client,
                    base_url=api_url,
                    token=token,
                    asset_id=asset["id"],
                    file_buffer=file_buffer,
                    filename=filename,
                    name=object_name,
                    description=object_description,
                    tags=tags,
                )
                created_objects.append(obj)
                _logger.info(
                    "Uploaded object: filename=%s, object_id=%s",
                    filename,
                    obj.get("id"),
                )
            except Exception as e:
                should_continue = handle_upload_error(e, filename, asset["id"])
                if not should_continue:
                    # Re-raise if we shouldn't continue
                    raise
        finally:
            if file_buffer:
                file_buffer.close()

    return created_assets, created_objects


def create_fixtures(
    client: httpx.Client,
    api_url: str,
    token: str,
    args,
) -> Tuple[List[dict], List[dict]]:
    """Create all fixtures (assets and objects).

    Returns:
        Tuple of (created_assets, created_objects) lists
    """
    all_assets = []
    all_objects = []

    for asset_idx in range(args.num_assets):
        assets, objects = create_asset_with_objects(
            client=client,
            api_url=api_url,
            token=token,
            asset_idx=asset_idx,
            num_assets=args.num_assets,
            objects_per_asset=args.objects_per_asset,
        )
        all_assets.extend(assets)
        all_objects.extend(objects)

    return all_assets, all_objects


def handle_main_error(e: Exception):
    """Handle errors at the main execution level."""
    _logger.exception("Error during fixture generation")
    _logger.error(
        "The script makes HTTP calls to the API server. "
        "Ensure the API server is running and properly configured."
    )


def main():
    """Main workflow to create fixtures."""
    # Load environment files first
    load_env_files()

    args = parse_args()

    # Validate configuration
    api_url = validate_configuration(args)

    # Authenticate with Keycloak
    token = authenticate_with_keycloak(args)

    # Create HTTP client for API calls
    client = httpx.Client(timeout=60.0)  # 60 second timeout for file uploads

    try:
        # Create all fixtures
        created_assets, created_objects = create_fixtures(
            client=client,
            api_url=api_url,
            token=token,
            args=args,
        )

        # Summary
        _logger.info(
            "Fixture generation completed successfully: assets=%d, objects=%d",
            len(created_assets),
            len(created_objects),
        )
    except Exception as e:
        handle_main_error(e)
        raise
    finally:
        # Close HTTP client
        client.close()


if __name__ == "__main__":
    setup_logging()
    main()
