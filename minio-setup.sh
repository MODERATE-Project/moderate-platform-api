#!/usr/bin/env bash

set -exu

(apt-get update -y && apt-get install -y curl || true) 2>/dev/null

curl https://dl.min.io/client/mc/release/linux-amd64/mc \
    --create-dirs \
    -o /usr/local/bin/mc

chmod +x /usr/local/bin/mc

mc alias set moderateapi "${MINIO_URL}" "${MINIO_USER}" "${MINIO_PASS}"
mc mb -p "moderateapi/${BUCKET_NAME}"
