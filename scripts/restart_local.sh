#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
UI_PORT="${UI_PORT:-8788}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
RUN_DIR="${ROOT_DIR}/.run"
mkdir -p "${RUN_DIR}"

BACKEND_LOG="${RUN_DIR}/backend.log"
UI_LOG="${RUN_DIR}/cloudflare-ui.log"

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" || true)"
  if [[ -n "${pids}" ]]; then
    echo "${pids}" | xargs kill >/dev/null 2>&1 || true
    sleep 1
    pids="$(lsof -ti "tcp:${port}" || true)"
    if [[ -n "${pids}" ]]; then
      echo "${pids}" | xargs kill -9 >/dev/null 2>&1 || true
    fi
  fi
}

start_backend() {
  kill_port "${BACKEND_PORT}"
  nohup "${ROOT_DIR}/.venv/bin/uvicorn" app.main:app --reload --port "${BACKEND_PORT}" >"${BACKEND_LOG}" 2>&1 &
  echo "$!" > "${RUN_DIR}/backend.pid"
}

start_ui() {
  kill_port "${UI_PORT}"
  (
    cd "${ROOT_DIR}/cloudflare-ui"
    nohup npx wrangler dev --local --port "${UI_PORT}" --var "BACKEND_BASE_URL:${BACKEND_URL}" >"${UI_LOG}" 2>&1 &
    echo "$!" > "${RUN_DIR}/ui.pid"
  )
}

MODE="${1:-all}"
case "${MODE}" in
  backend)
    start_backend
    ;;
  ui)
    start_ui
    ;;
  all)
    start_backend
    start_ui
    ;;
  *)
    echo "Usage: $0 [all|backend|ui]"
    exit 1
    ;;
esac

echo "restarted mode=${MODE}"
echo "backend: ${BACKEND_URL}  log=${BACKEND_LOG}"
echo "ui:      http://127.0.0.1:${UI_PORT}  log=${UI_LOG}"
