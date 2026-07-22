#!/bin/sh
echo "Current working directory: $(pwd)"
echo "Environment PORT: $PORT"
PORT="${PORT:-8000}"
echo "Starting Uvicorn on port $PORT..."
exec uvicorn API.main:app --host 0.0.0.0 --port $PORT
