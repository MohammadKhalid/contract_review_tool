#!/bin/bash
set -e

echo "Waiting for database to be ready for migrations..."

# The compose healthcheck + depends_on should make the DB available,
# but we add a small retry loop for extra robustness (especially on slow CI or first boot).
for i in $(seq 1 30); do
    if alembic current >/dev/null 2>&1 || alembic upgrade head --sql >/dev/null 2>&1; then
        echo "Database is reachable."
        break
    fi
    echo "Database not ready yet (attempt $i/30)..."
    sleep 1
done

echo "Running Alembic migrations (upgrade head)..."
alembic upgrade head
echo "Migrations complete."

echo "Starting application..."
exec uvicorn app:app --host 0.0.0.0 --port 5001
