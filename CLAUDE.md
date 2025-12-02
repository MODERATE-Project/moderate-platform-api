# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the HTTP API for the MODERATE platform, which serves as the public entry point for developers to interact with data assets and services. The project consists of:

- **API Backend**: FastAPI-based HTTP API (`moderate_api/`)
- **Web UI**: React/TypeScript frontend (`moderate_ui/`)

The API integrates with:

- **Keycloak** (authentication via APISIX gateway)
- **PostgreSQL** (main database via SQLModel)
- **S3-compatible storage** (MinIO locally, GCS for production)
- **RabbitMQ** (message queue for long-running tasks)
- **Trust Services** (optional - IOTA DLT cryptographic proofs)
- **OpenMetadata** (optional - data discovery and profiling)

## Development Commands

### Setup and Running

Start the full development stack (includes APISIX, Keycloak, PostgreSQL, MinIO, Trust Services):

```bash
task dev-up
```

Start with GCS instead of MinIO:

```bash
ACCESS_KEY="..." SECRET_KEY="..." task dev-up-gcs
```

Stop and clean up development stack:

```bash
task dev-down
```

Run the UI in development mode (requires Keycloak running):

```bash
task ui-run-dev
# Or directly:
cd moderate_ui && npm run dev
```

### Testing

Run the full test suite (automatically starts/stops test dependencies):

```bash
task test
```

Start test dependencies manually:

```bash
task test-deps-up
```

Run tests with Poetry directly (requires test deps running):

```bash
poetry run pytest -v
```

Run a single test file:

```bash
poetry run pytest tests/test_asset.py -v
```

Run a specific test:

```bash
poetry run pytest tests/test_asset.py::test_function_name -v
```

Stop test dependencies:

```bash
task test-deps-down
```

### Code Quality

Format code with Black:

```bash
poetry run black moderate_api/ tests/
```

### Database Migrations

Create a new Alembic migration:

```bash
task alembic-revision MSG="Description of changes"
# Or with default message based on git commit:
task alembic-revision
```

Apply migrations (requires MIGRATIONS_SQLALCHEMY_URL env var):

```bash
MIGRATIONS_SQLALCHEMY_URL="postgresql://..." task alembic-upgrade
```

### API Documentation

Generate OpenAPI spec and static documentation:

```bash
task swagger-codegen-docs
```

The API docs are auto-generated at `/docs` (Swagger) and `/redoc` (ReDoc) when running.

### Version Management

Bump versions (must be on clean git state):

```bash
task bump VERSION_API="0.3.0" VERSION_UI="0.3.0"
```

Commit, tag, and bump in one command:

```bash
task bump-commit-tag VERSION_API="0.3.0"
```

## Architecture

### Backend Structure

The API follows a modular architecture:

```
moderate_api/
├── main.py              # FastAPI app initialization, lifespan, middleware
├── config.py            # Settings (uses Pydantic BaseSettings with env vars)
├── db.py                # Database engine and session management
├── enums.py             # Shared enums (Entities, Actions, Prefixes, etc.)
├── authz/               # Authentication and authorization
│   ├── token.py         # JWT token validation (Keycloak)
│   ├── user.py          # User model and dependencies
│   ├── enforcer.py      # Casbin policy enforcement
│   └── casbin_*.{conf,csv}  # Casbin RBAC configuration
├── entities/            # Core domain entities
│   ├── crud.py          # Generic CRUD operations with filtering/sorting
│   ├── asset/           # Data assets (with S3 objects)
│   ├── user/            # User profiles and metadata
│   ├── access_request/  # Access requests to assets
│   ├── job/             # Long-running workflow jobs
│   └── visualization/   # Data visualizations (PyGWalker)
├── notebooks/           # Marimo notebooks for data analysis
│   ├── exploration/     # Exploratory data analysis
│   └── synthethic_load/ # Synthetic load generation (ML model)
├── object_storage.py    # S3/MinIO client management
├── message_queue.py     # RabbitMQ integration
├── long_running.py      # Background task management
├── trust.py             # IOTA DLT integration (proofs)
└── open_metadata.py     # OpenMetadata integration
```

**Key architectural patterns:**

1. **Entity-Router-Model Pattern**: Each entity has `router.py` (endpoints), `models.py` (SQLModel/Pydantic schemas)

2. **CRUD Layer** (`entities/crud.py`): Generic CRUD operations with:

   - Query parameter parsing (`CrudFiltersQuery`, `CrudSortsQuery`)
   - JSON-based advanced filtering (comparison operators, JSONB queries)
   - Authorization integration via Casbin
   - Pagination with total count headers

3. **Authorization**: Two-layer approach

   - **Authentication**: JWT tokens from Keycloak, validated via OIDC
   - **Authorization**: Casbin RBAC with roles `api_admin` and `api_basic_access`
   - Roles are client-level roles in the `apisix` Keycloak client

4. **Dependency Injection**: Extensive use of FastAPI dependencies:

   - `UserDep` / `OptionalUserDep` - Current user
   - `AsyncSessionDep` - Database session
   - `SettingsDep` - Application settings
   - `S3ClientDep` - S3 client
   - `EnforcerDep` - Casbin enforcer

5. **Long-Running Tasks**: Background tasks stored in DB with status tracking via `/jobs` endpoints

6. **Notebooks**: Marimo notebooks mounted as ASGI apps, authenticated via cookie middleware

### Frontend Structure

The UI uses Refine.dev framework with Mantine components:

```
moderate_ui/
├── src/
│   ├── App.tsx          # Main app with Refine setup
│   ├── pages/           # Page components
│   │   ├── assets/      # Asset CRUD pages
│   │   ├── notebooks/   # Notebook container pages
│   │   └── asset-objects/  # Object-level pages
│   ├── components/      # Reusable components
│   ├── api/             # API client functions
│   ├── auth-provider/   # Keycloak integration
│   └── rest-data-provider/  # Custom REST data provider
```

The UI communicates with the API backend and embeds Marimo notebooks via iframes.

### Database Models

SQLModel is used for both SQLAlchemy ORM and Pydantic validation. Models use inheritance:

- `*Base`: Base table structure (inherits from `SQLModel, table=True`)
- `*Create`: Creation schema (excludes ID, timestamps)
- `*Update`: Update schema (all fields optional)
- `*Read`: Read schema with computed fields

Example: `Asset`, `AssetCreate`, `AssetUpdate`, `AssetRead`

### Configuration

All configuration uses environment variables with the prefix `MODERATE_API_`:

- Nested config uses `__` (e.g., `MODERATE_API_S3__ACCESS_KEY`)
- See `config.py` for full schema
- Local dev: `.env.dev` and `.env.dev.default`
- Tests: Environment variables set in `tests/conftest.py`

## Important Conventions

### Authentication in Development

To create an admin user in local Keycloak:

1. Access Keycloak at `http://localhost:8989` (credentials in `.env.dev.default`)
2. Create a user in the `moderate` realm
3. Assign the `api_admin` role to the user in the `apisix` **client** (not realm-level role)

For basic access, assign `api_basic_access` role.

### Testing

Tests use pytest with async support (`pytest-asyncio`). Test fixtures:

- `access_token`: Generate test JWT tokens with configurable roles
- `client`: FastAPI TestClient
- `s3`: S3 client (skips if MinIO offline)
- `drop_all_tables`: Auto-cleanup after each test
- `skip_if_db_offline`: Auto-skip if PostgreSQL offline

Test environment variables are configured in `conftest.py`.

### Running Single Components

To run just the API (without Docker):

```bash
poetry run uvicorn moderate_api.main:app --reload
```

To run just the UI:

```bash
cd moderate_ui && npm run dev
```

Note: Both require external services (PostgreSQL, Keycloak, S3, etc.) to be running.

### S3 Object Storage

The API supports any S3-compatible storage:

- **Local dev**: MinIO (via docker-compose)
- **Production**: GCS S3-compatible interface or any S3 service
- Configuration: `MODERATE_API_S3__*` environment variables

### Trust Services (Optional)

To enable Trust Services integration:

1. Create `.env.trust.local` with `L2_PRIVATE_KEY`
2. Authenticate with GCP Artifact Registry: `gcloud auth configure-docker europe-west1-docker.pkg.dev`
3. Trust Services will start with `task dev-up`

If unavailable, the API continues to function without DLT features.

### Notebooks

Notebooks are Marimo applications served as ASGI apps:

- Defined in `moderate_api/notebooks/`
- Registered in `ALL_NOTEBOOKS` dict
- Mounted at paths like `/notebook-exploration`
- Authenticated via JWT cookie set by middleware

To add a new notebook:

1. Create module in `moderate_api/notebooks/your_notebook/`
2. Add `notebook.py` file (Marimo app)
3. Register in `moderate_api/notebooks/__init__.py`
4. Add enum in `enums.py:Notebooks`

### API Routes

All API routes are prefixed (see `enums.py:Prefixes`):

- `/ping` - Health check
- `/assets` - Asset management
- `/users` - User profiles
- `/access-requests` - Access request workflows
- `/jobs` - Long-running tasks
- `/visualizations` - Data visualizations

Trailing slashes are forbidden and will cause the app to abort on startup.

## Key Files to Understand

When working on specific features, focus on these files:

**Authentication/Authorization:**

- `moderate_api/authz/token.py` - Token validation
- `moderate_api/authz/enforcer.py` - Casbin RBAC
- `moderate_api/authz/user.py` - User extraction

**CRUD Operations:**

- `moderate_api/entities/crud.py` - Generic CRUD with filtering/sorting/pagination

**Assets (core entity):**

- `moderate_api/entities/asset/models.py` - Asset and S3Object models
- `moderate_api/entities/asset/router.py` - Asset endpoints (170+ lines)

**Database:**

- `moderate_api/db.py` - Engine singleton and session factory

**Configuration:**

- `moderate_api/config.py` - All settings
- `.env.dev.default` - Default local config
- `Taskfile.yml` - Task runner configuration

## Docker Compose Stacks

- `docker-compose-dev.yml` - Full development stack
- `docker-compose-tests.yml` - Test dependencies only
- `docker-compose-trust.yml` - Trust Services (optional)

All stacks use the project name `moderateapi` (or `moderateapi_tests`).
