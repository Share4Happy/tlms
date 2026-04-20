#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os
import sys

async def check():
    try:
        url = os.environ.get('DATABASE_URL')
        if not url:
            print('DATABASE_URL is not set', file=sys.stderr)
            sys.exit(1)
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(check())
"; do
    sleep 1
done
echo "Database is ready!"

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
