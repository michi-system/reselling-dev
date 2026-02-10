#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
CLOUDFLARED_PID_FILE="${RUN_DIR}/cloudflared.pid"

if [[ ! -f "${CLOUDFLARED_PID_FILE}" ]]; then
  echo "cloudflared pidがありません（既に停止している可能性があります）"
  exit 0
fi

pid="$(cat "${CLOUDFLARED_PID_FILE}" || true)"
if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
  kill "${pid}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${pid}" 2>/dev/null; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
  echo "cloudflaredを停止しました pid=${pid}"
else
  echo "cloudflaredは停止済みです"
fi

rm -f "${CLOUDFLARED_PID_FILE}"
