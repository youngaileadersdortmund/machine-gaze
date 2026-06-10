#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_URL="${INFERENCE_BACKEND_URL:-http://localhost:${BACKEND_PORT}}"
WORKER_TOKEN="${INFERENCE_WORKER_TOKEN:-${WORKER_TOKEN:-dev-worker-token}}"
INFERENCE_MODE="${INFERENCE_ANALYZER:-qwen}"

if [ -f "${HOME}/.profile" ]; then
  # Helpful on clusters where Node is loaded through nvm from the login profile.
  # shellcheck disable=SC1090
  source "${HOME}/.profile" || true
fi

command -v uv >/dev/null 2>&1 || {
  echo "uv is required but was not found in PATH." >&2
  exit 1
}

command -v npm >/dev/null 2>&1 || {
  echo "npm is required but was not found in PATH. Load Node.js first." >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required but was not found in PATH." >&2
  exit 1
}

pids=()

cleanup() {
  echo
  echo "Stopping Machine Gaze services..."
  for pid in "${pids[@]:-}"; do
    kill "${pid}" >/dev/null 2>&1 || true
  done
  wait >/dev/null 2>&1 || true
}

trap cleanup INT TERM EXIT

start_service() {
  local name="$1"
  local directory="$2"
  local command="$3"

  (
    cd "${directory}"
    echo "[${name}] starting"
    bash -lc "${command}"
  ) &
  pids+=("$!")
}

wait_for_backend() {
  local health_url="http://localhost:${BACKEND_PORT}/health"

  echo "[backend] waiting for ${health_url}"
  for _ in $(seq 1 60); do
    if python3 - "${health_url}" >/dev/null 2>&1 <<'PY'
import sys
import urllib.request

urllib.request.urlopen(sys.argv[1], timeout=2).read()
PY
    then
      echo "[backend] health check is ready"
      return 0
    fi

    sleep 1
  done

  echo "Backend did not become healthy at ${health_url}" >&2
  exit 1
}

start_service "backend" "${ROOT_DIR}/backend" \
  "uv sync && uv run uvicorn backend.app:app --host 0.0.0.0 --port ${BACKEND_PORT}"

if [ ! -d "${ROOT_DIR}/frontend/node_modules" ]; then
  echo "[frontend] installing npm dependencies"
  (cd "${ROOT_DIR}/frontend" && npm install)
fi

start_service "frontend" "${ROOT_DIR}/frontend" \
  "npm run dev -- --hostname 0.0.0.0 --port ${FRONTEND_PORT}"

wait_for_backend

if [ "${INFERENCE_MODE}" = "stub" ]; then
  start_service "inference" "${ROOT_DIR}/inference" \
    "uv sync && INFERENCE_ANALYZER=stub uv run inference-worker --daemon --backend-url ${BACKEND_URL} --worker-token ${WORKER_TOKEN}"
else
  start_service "inference" "${ROOT_DIR}/inference" \
    "uv sync --group gpu && uv run --group gpu inference-worker --daemon --analyzer ${INFERENCE_MODE} --backend-url ${BACKEND_URL} --worker-token ${WORKER_TOKEN}"
fi

cat <<EOF

Machine Gaze is starting.

Frontend: http://localhost:${FRONTEND_PORT}
Backend:  http://localhost:${BACKEND_PORT}/health
Worker:   ${INFERENCE_MODE}

If this is running on a remote cluster node, open a tunnel from your laptop:

  ssh -L ${FRONTEND_PORT}:localhost:${FRONTEND_PORT} -L ${BACKEND_PORT}:localhost:${BACKEND_PORT} <user>@<host>

Press Ctrl+C to stop all services.
EOF

wait -n "${pids[@]}"
