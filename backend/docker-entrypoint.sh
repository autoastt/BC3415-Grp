#!/bin/sh
set -e
if [ "${SEED_SAMPLE_DATA:-true}" = "true" ]; then
  python -m scripts.seed || echo "Sample data not loaded (check your embedding API key)."
fi
# One worker: the rate limiter and settings cache are in-process.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
