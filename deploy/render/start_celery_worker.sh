#!/usr/bin/env bash
set -euo pipefail

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
exec celery -A core worker -l info
