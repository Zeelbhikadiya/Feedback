#!/bin/sh
set -e

echo "Running DB bootstrap..."
python - <<'PY'
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print("Tables ready.")
PY

if [ "${SEED_ON_STARTUP:-false}" = "true" ]; then
  echo "Seeding demo data (SEED_ON_STARTUP=true)..."
  python seed.py || true
fi

PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
