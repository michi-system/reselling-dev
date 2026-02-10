#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_LOCAL_URL="http://127.0.0.1:${BACKEND_PORT}"
PUBLIC_HEALTH_WAIT_SECONDS="${PUBLIC_HEALTH_WAIT_SECONDS:-30}"
TUNNEL_RETRY_COUNT="${TUNNEL_RETRY_COUNT:-2}"
CLOUDFLARED_LOG="${RUN_DIR}/cloudflared.log"
CLOUDFLARED_PID_FILE="${RUN_DIR}/cloudflared.pid"
SHARE_BACKEND_URL_FILE="${RUN_DIR}/share_backend_url.txt"
SHARE_WORKER_URL_FILE="${RUN_DIR}/share_worker_url.txt"
WORKER_DIR="${ROOT_DIR}/cloudflare-ui"

mkdir -p "${RUN_DIR}"

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: '${cmd}' が見つかりません。インストールしてください。"
    exit 1
  fi
}

stop_existing_cloudflared() {
  if [[ -f "${CLOUDFLARED_PID_FILE}" ]]; then
    local old_pid
    old_pid="$(cat "${CLOUDFLARED_PID_FILE}" || true)"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      kill "${old_pid}" >/dev/null 2>&1 || true
      sleep 1
    fi
  fi
}

extract_tunnel_url() {
  local max_wait_seconds="${1:-60}"
  local elapsed=0
  while [[ "${elapsed}" -lt "${max_wait_seconds}" ]]; do
    if [[ -f "${CLOUDFLARED_LOG}" ]]; then
      local url
      url="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' "${CLOUDFLARED_LOG}" | tail -n1 || true)"
      if [[ -n "${url}" ]]; then
        echo "${url}"
        return 0
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

wait_for_backend_health() {
  local max_wait_seconds="${1:-30}"
  local elapsed=0
  while [[ "${elapsed}" -lt "${max_wait_seconds}" ]]; do
    if curl -fsS "${BACKEND_LOCAL_URL}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

wait_for_public_health() {
  local url="$1"
  local max_wait_seconds="${2:-60}"
  local elapsed=0
  while [[ "${elapsed}" -lt "${max_wait_seconds}" ]]; do
    if curl -fsS "${url}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

start_tunnel_and_get_url() {
  : > "${CLOUDFLARED_LOG}"
  nohup cloudflared tunnel --url "${BACKEND_LOCAL_URL}" --no-autoupdate >"${CLOUDFLARED_LOG}" 2>&1 &
  local tunnel_pid="$!"
  echo "${tunnel_pid}" > "${CLOUDFLARED_PID_FILE}"
  extract_tunnel_url 60
}

extract_worker_url() {
  local deploy_output="$1"
  local url
  url="$(echo "${deploy_output}" | grep -Eo 'https://[a-zA-Z0-9.-]+\.workers\.dev' | head -n1 || true)"
  echo "${url}"
}

main() {
  require_cmd cloudflared
  require_cmd curl
  require_cmd npx

  echo "[1/5] backend再起動"
  bash "${ROOT_DIR}/scripts/restart_local.sh" backend >/dev/null
  if ! wait_for_backend_health 45; then
    echo "ERROR: backend起動待ちタイムアウト"
    exit 1
  fi

  echo "[2/5] 既存cloudflared停止"
  stop_existing_cloudflared

  echo "[3/5] cloudflared起動"
  local tunnel_url=""
  local attempt=1
  while [[ "${attempt}" -le "${TUNNEL_RETRY_COUNT}" ]]; do
    stop_existing_cloudflared
    if tunnel_url="$(start_tunnel_and_get_url)"; then
      if wait_for_public_health "${tunnel_url}" "${PUBLIC_HEALTH_WAIT_SECONDS}"; then
        break
      fi
    fi
    echo "WARN: tunnel起動リトライ (${attempt}/${TUNNEL_RETRY_COUNT})"
    attempt=$((attempt + 1))
  done
  if [[ -z "${tunnel_url}" ]]; then
    echo "ERROR: 公開backendのURL取得に失敗しました"
    echo "---- cloudflared.log ----"
    tail -n 120 "${CLOUDFLARED_LOG}" || true
    exit 1
  fi
  if ! wait_for_public_health "${tunnel_url}" 3; then
    echo "WARN: 公開backendのヘルス確認は失敗しました（DNS伝播待ちの可能性あり）。そのままデプロイします。"
  fi
  echo "${tunnel_url}" > "${SHARE_BACKEND_URL_FILE}"

  echo "[4/5] Cloudflare Workerデプロイ"
  local deploy_output
  deploy_output="$(cd "${WORKER_DIR}" && npx wrangler deploy --var "BACKEND_BASE_URL:${tunnel_url}" 2>&1)"
  echo "${deploy_output}"

  local worker_url
  worker_url="$(extract_worker_url "${deploy_output}")"
  if [[ -z "${worker_url}" ]]; then
    echo "ERROR: Worker URL の抽出に失敗しました。"
    exit 1
  fi
  echo "${worker_url}" > "${SHARE_WORKER_URL_FILE}"

  echo "[5/5] 疎通確認"
  curl -fsS "${worker_url}/health" >/dev/null
  curl -fsS "${worker_url}/api/system/thresholds?category=audio" >/dev/null

  echo ""
  echo "共有反映完了"
  echo "Backend(公開): ${tunnel_url}"
  echo "UI(Cloudflare): ${worker_url}"
  echo "メモ:"
  echo "- cloudflaredが停止すると公開Backendは使えなくなります。"
  echo "- 次回も同じコマンドでURL更新 + 再デプロイできます。"
}

main "$@"
