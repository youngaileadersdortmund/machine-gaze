#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [ -f "${HOME}/.profile" ]; then
  # Helpful on clusters where Node is loaded through nvm from the login profile.
  # shellcheck disable=SC1090
  source "${HOME}/.profile" || true
fi

load_env_default() {
  local key="$1"
  local env_file="${ROOT_DIR}/.env"
  local line
  local value

  if [ -n "${!key:-}" ] || [ ! -f "${env_file}" ]; then
    return 0
  fi

  line="$(grep -E "^[[:space:]]*${key}=" "${env_file}" | tail -n 1 || true)"
  if [ -z "${line}" ]; then
    return 0
  fi

  value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"

  if [ -n "${value}" ]; then
    export "${key}=${value}"
  fi
}

for key in \
  INFERENCE_BACKEND_URL \
  INFERENCE_WORKER_TOKEN \
  WORKER_TOKEN \
  GOOGLE_CLOUD_PROJECT \
  GOOGLE_CLOUD_LOCATION \
  GEMINI_MODEL_ID \
  GEMINI_TEMPERATURE \
  INFERENCE_MAX_OUTPUT_TOKENS
do
  load_env_default "${key}"
done

BACKEND_URL="${INFERENCE_BACKEND_URL:-http://localhost:${BACKEND_PORT}}"
WORKER_TOKEN="${INFERENCE_WORKER_TOKEN:-${WORKER_TOKEN:-dev-worker-token}}"
SKIP_INFERENCE="${SKIP_INFERENCE:-0}"

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

if [ -n "${VIRTUAL_ENV:-}" ]; then
  echo "Ignoring active virtualenv from another project: ${VIRTUAL_ENV}"
  unset VIRTUAL_ENV
fi

if [ "${SKIP_INFERENCE}" != "1" ] && [ -z "${GOOGLE_CLOUD_PROJECT:-}" ]; then
  cat >&2 <<'EOF'
GOOGLE_CLOUD_PROJECT is required before starting the Gemini inference worker.

Run:
  gcloud auth application-default login
  gcloud auth application-default set-quota-project your-project-id
  export GOOGLE_CLOUD_PROJECT=your-project-id
  export GOOGLE_CLOUD_LOCATION=us-central1

Or put these values in .env.

To start only backend and frontend for UI work:
  SKIP_INFERENCE=1 ./scripts/run-dev.sh
EOF
  exit 1
fi

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

if [ "${SKIP_INFERENCE}" != "1" ]; then
  start_service "inference" "${ROOT_DIR}/inference" \
    "uv sync && uv run inference-worker --daemon --backend-url ${BACKEND_URL} --worker-token ${WORKER_TOKEN}"
fi

cat <<EOF

Machine Gaze is starting.

Frontend: http://localhost:${FRONTEND_PORT}
Backend:  http://localhost:${BACKEND_PORT}/health
Worker:   $(if [ "${SKIP_INFERENCE}" = "1" ]; then echo "skipped"; else echo "Gemini Big Five inference"; fi)

If this is running on a remote cluster node, open a tunnel from your laptop:

  ssh -L ${FRONTEND_PORT}:localhost:${FRONTEND_PORT} -L ${BACKEND_PORT}:localhost:${BACKEND_PORT} <user>@<host>

Press Ctrl+C to stop all services.
EOF

wait -n "${pids[@]}"
