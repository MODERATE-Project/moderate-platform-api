#!/bin/bash

set -e
set -x

echo "CREATE DATABASE moderateapi;" |
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"

echo "CREATE EXTENSION pg_trgm;" |
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "moderateapi"

echo "CREATE EXTENSION btree_gin;" |
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "moderateapi"
