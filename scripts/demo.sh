#!/usr/bin/env bash
set -euo pipefail
DEMO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEMO_ROOT"
if [[ ! -f .env.demo ]]; then
  python3 scripts/demo.py init
fi
set -a
source .env.demo
set +a
export PYTHONPATH="$DEMO_ROOT"
case "${1:-help}" in
  setup)
    python3 -c 'import sys; sys.exit("É necessário Python 3.12 ou superior.") if sys.version_info < (3, 12) else None'
    python3 -m venv .venv
    .venv/bin/pip install -r requirements-dev.txt
    docker compose --env-file .env.demo -f compose.demo.yml up -d --wait db
    .venv/bin/python -m scripts.create_db
    ;;
  api)
    exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
    ;;
  seed)
    exec .venv/bin/python scripts/demo.py seed
    ;;
  credentials)
    exec .venv/bin/python scripts/demo.py credentials
    ;;
  provision)
    exec .venv/bin/python scripts/provision_demo.py "${@:2}"
    ;;
  build-web)
    cd "${FLIKE_FRONTEND_DIR:-$DEMO_ROOT/../flike-frontend-webpage}"
    npm ci
    NEXT_PUBLIC_API_URL="$DEMO_API_URL" npm run build
    ;;
  web)
    cd "${FLIKE_FRONTEND_DIR:-$DEMO_ROOT/../flike-frontend-webpage}"
    NEXT_PUBLIC_API_URL="$DEMO_API_URL" exec npm run start -- --hostname 127.0.0.1 --port 3000
    ;;
  test)
    docker compose --env-file .env.demo -f compose.demo.yml --profile test up -d --wait db-test
    export DB_PORT=55471 DB_DATABASE=flike_test FLIKE_TEST_DATABASE=1
    .venv/bin/python -m scripts.create_db
    exec .venv/bin/python -m pytest tests -q "${@:2}"
    ;;
  e2e)
    docker compose --env-file .env.demo -f compose.demo.yml --profile test up -d --wait db-test
    export DB_PORT=55471 DB_DATABASE=flike_test FLIKE_TEST_DATABASE=1
    .venv/bin/python -m scripts.create_db
    .venv/bin/python -m playwright install chromium
    exec .venv/bin/python scripts/run_e2e.py
    ;;
  stop)
    docker compose --env-file .env.demo -f compose.demo.yml --profile test stop
    ;;
  *)
    echo "Uso: $0 {setup|api|seed|credentials|provision <lock_id>|build-web|web|test|e2e|stop}"
    ;;
esac
