#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
if [ $# -gt 0 ]; then
    # If arguments are passed (e.g., celery command), run them
    exec "$@"
else
    # Default: run uvicorn
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
