#!/usr/bin/env bash
set -euo pipefail

# This script works in two layouts:
# 1) docker-compose dev mounts ./app -> /usr/src/app (manage.py at /usr/src/app/manage.py)
# 2) built image copies repo root -> /usr/src/app (manage.py at /usr/src/app/app/manage.py)

ROOT="/usr/src/app"
cd "$ROOT"

if [[ -f "manage.py" ]]; then
  DJANGO_DIR="$ROOT"
elif [[ -f "app/manage.py" ]]; then
  DJANGO_DIR="$ROOT/app"
else
  echo "manage.py not found" >&2
  exit 1
fi

cd "$DJANGO_DIR"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Render provides PORT; default for local safety
PORT="${PORT:-8000}"
exec daphne core.asgi:application -b 0.0.0.0 -p "$PORT"
