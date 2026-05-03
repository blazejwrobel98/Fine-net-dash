#!/usr/bin/env bash
# Install / refresh Python venv and optional systemd user service for Fine Net Dash.
# Run from the extracted tarball: ./scripts/install-linux.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${APP_ROOT}"

PORT="${PORT:-8000}"
SKIP_SYSTEMD="${SKIP_SYSTEMD:-0}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.11+ (e.g. apt install python3 python3-venv)." >&2
  exit 1
fi

if [[ ! -f "${APP_ROOT}/backend/app/main.py" ]]; then
  echo "Expected backend at ${APP_ROOT}/backend — wrong working tree?" >&2
  exit 1
fi

VENV="${APP_ROOT}/venv"
REQ="${APP_ROOT}/backend/requirements-prod.txt"
if [[ ! -f "${REQ}" ]]; then
  REQ="${APP_ROOT}/backend/requirements.txt"
fi

if [[ ! -d "${VENV}" ]]; then
  echo "Creating venv at ${VENV}..."
  python3 -m venv "${VENV}"
fi

echo "pip install..."
"${VENV}/bin/pip" install --upgrade pip >/dev/null
"${VENV}/bin/pip" install -r "${REQ}"

mkdir -p "${APP_ROOT}/backend/data"

UNIT="${HOME}/.config/systemd/user/fine-net-dash.service"
# SQLAlchemy absolute SQLite URL: sqlite://// + path-without-leading-slash
_DB_PATH="${APP_ROOT}/backend/data/portfolio.db"
_DB_URL="sqlite:////${_DB_PATH#/}"

if [[ "${SKIP_SYSTEMD}" == "1" ]]; then
  echo "Skipping systemd (SKIP_SYSTEMD=1)."
  echo "Start manually:"
  echo "  cd ${APP_ROOT}/backend && ${VENV}/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${PORT}"
  exit 0
fi

if command -v systemctl >/dev/null 2>&1; then
  mkdir -p "${HOME}/.config/systemd/user"
  cat >"${UNIT}" <<EOF
[Unit]
Description=Fine Net Dash (uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_ROOT}/backend
Environment=DATABASE_URL=${_DB_URL}
Environment=SKIP_SCHEDULER=0
ExecStart=${VENV}/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${PORT}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
  echo "Wrote ${UNIT}"
  systemctl --user daemon-reload
  systemctl --user enable fine-net-dash.service
  echo "Enabled user service. Start with:"
  echo "  systemctl --user start fine-net-dash"
  echo "  journalctl --user -u fine-net-dash -f"
else
  echo "systemctl not available; start manually:"
  echo "  cd ${APP_ROOT}/backend && ${VENV}/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${PORT}"
fi
