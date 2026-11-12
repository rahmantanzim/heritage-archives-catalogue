#!/bin/sh
# Start the API in Docker: create or upgrade the tables, load the data,
# then run the server. DATA_DIR picks the data (default: the sample).
set -eu

alembic upgrade head
python -m ha_catalogue.load "${DATA_DIR:-data/sample}"
exec uvicorn ha_catalogue.api:create_app --factory --host 0.0.0.0 --port 8000
