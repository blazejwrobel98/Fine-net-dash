#!/usr/bin/env bash
# Build frontend and create release/FineNetDash-linux-amd64.tar.gz (portable tree + install-linux.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required to build the frontend." >&2
  exit 1
fi

echo "npm ci + build (frontend)..."
pushd "${ROOT}/frontend" >/dev/null
npm ci
npm run build
popd >/dev/null

STAGE="${ROOT}/release/stage_linux"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/FineNetDash"

echo "Staging files..."
cp -a "${ROOT}/backend" "${STAGE}/FineNetDash/"
rm -rf "${STAGE}/FineNetDash/backend/tests" \
  "${STAGE}/FineNetDash/backend/__pycache__" \
  "${STAGE}/FineNetDash/backend/.pytest_cache" 2>/dev/null || true
find "${STAGE}/FineNetDash/backend" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

mkdir -p "${STAGE}/FineNetDash/frontend/dist"
cp -a "${ROOT}/frontend/dist/." "${STAGE}/FineNetDash/frontend/dist/"

mkdir -p "${STAGE}/FineNetDash/scripts"
cp "${ROOT}/scripts/migrate_portfolio_db.py" "${STAGE}/FineNetDash/scripts/"
cp "${ROOT}/scripts/install-linux.sh" "${STAGE}/FineNetDash/scripts/"
chmod +x "${STAGE}/FineNetDash/scripts/install-linux.sh"

cp "${ROOT}/LICENSE" "${STAGE}/FineNetDash/" 2>/dev/null || true
cp "${ROOT}/README.md" "${STAGE}/FineNetDash/" 2>/dev/null || true
if [[ -f "${ROOT}/docs/Zastrzezenia-prawne.md" ]]; then
  cp "${ROOT}/docs/Zastrzezenia-prawne.md" "${STAGE}/FineNetDash/"
fi

cat >"${STAGE}/FineNetDash/INSTALL.linux.txt" <<'EOF'
Fine Net Dash — Linux (paczka przenośna, pre-alfa)

1. Rozpakuj archiwum w dowolnym katalogu (np. w swoim katalogu domowym).
2. Na komputerze docelowym potrzebny jest tylko Python 3.11+ (frontend jest juz zbudowany w paczce).
3. Uruchom instalacje:
     cd FineNetDash/scripts
     ./install-linux.sh

   Opcjonalnie: SKIP_SYSTEMD=1 ./install-linux.sh  (tylko venv, bez unitu systemd)
   Opcjonalnie: PORT=8080 ./install-linux.sh

4. Otworz http://127.0.0.1:8000/ (domyslnie PORT=8000).

Baza danych: backend/data/portfolio.db (utworzy sie przy pierwszym uruchomieniu).

Uwaga: zalecamy uzycie lokalne / w zaufanej sieci — aplikacja nie ma wbudowanego logowania do API.
Zastrzezenia prawne: plik Zastrzezenia-prawne.md (jesli dolaczony).
EOF

OUT="${ROOT}/release/FineNetDash-linux-amd64.tar.gz"
mkdir -p "${ROOT}/release"
tar -czf "${OUT}" -C "${STAGE}" FineNetDash
echo "Created ${OUT}"
