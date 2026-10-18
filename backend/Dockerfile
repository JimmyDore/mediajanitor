# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and procps for pgrep (celery-beat healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl procps && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/

# Copy alembic configuration and migrations
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Run as non-root (uid 1000 matches the host owner of ./data); /app must be
# writable for celery-beat's schedule file
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --no-create-home app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Use entrypoint script to run migrations before starting the app
ENTRYPOINT ["./entrypoint.sh"]

