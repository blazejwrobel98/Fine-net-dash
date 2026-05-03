# Fine net dash / portfel dywidendowy

Web app for a manual dividend portfolio: universe of dividend stocks, purchase lots (including fractional), average cost, Yahoo Finance prices (`yfinance`), and optional ntfy alerts when price drops below your threshold.

Repository: [github.com/blazejwrobel98/Fine-net-dash](https://github.com/blazejwrobel98/Fine-net-dash)

**License:** [MIT](LICENSE) — use and run the project freely; no warranty.

## Stable releases (Docker, Linux, Windows)

Tag a version as `v*` (example `v0.2.0`) and push it. GitHub Actions **Release** workflow then:

| Artifact | Use case |
|----------|-----------|
| **Docker** | `docker pull ghcr.io/blazejwrobel98/fine-net-dash:v0.2.0` then `docker run -p 8000:8000 -v fine-data:/app/backend/data ghcr.io/blazejwrobel98/fine-net-dash:v0.2.0` — or use this repo’s `docker compose up --build` for a local image `fine-net-dash:local`. |
| **Linux** | Download `FineNetDash-linux-amd64.tar.gz` from [Releases](https://github.com/blazejwrobel98/Fine-net-dash/releases), extract, run `cd FineNetDash/scripts && ./install-linux.sh` (optional `SKIP_SYSTEMD=1`). |
| **Windows** | **ZIP:** unzip `DividendPortfolio.zip`, follow `INSTALL.txt` / `scripts\install-windows.ps1`. **MSI:** installs under `%LOCALAPPDATA%\Programs\FineNetDash\` — then run once: `powershell -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\Programs\FineNetDash\scripts\Install-AfterMsi.ps1"` (venv + Task Scheduler). |

Maintainers: build the MSI with [WiX](https://wixtoolset.org/) **6.x** (WiX 7+ needs [OSMF](https://wixtoolset.org/osmf/) acceptance): `dotnet tool install --global wix --version 6.0.2`, then `.\packaging\windows\build-msi.ps1 -Version 0.2.0.0`.

## What you need

| Component | Version |
|-----------|---------|
| Python | 3.11+ (tested on 3.13) |
| Node.js | 18+ (for the React frontend) |

Optional: **XTB is not integrated** — you enter tickers as on Yahoo (e.g. `PZU.WA`, `KO`).

---

## Run locally (recommended for development)

You run **two processes**: API (FastAPI) and the Vite dev server (UI with hot reload).

### 1. Backend

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # optional
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Linux / macOS**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- REST API: `http://127.0.0.1:8000/api/...`
- Set `SKIP_SCHEDULER=1` in `.env` or the environment if you want no background jobs (e.g. focused debugging).

### 2. Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** — Vite proxies `/api` to `http://127.0.0.1:8000`.

---

## Run as a single server (production-style)

Build the SPA so FastAPI can serve `frontend/dist` from the same port.

```bash
cd frontend && npm install && npm run build
cd ../backend
# activate venv as above
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/` (or `http://<your-LAN-IP>:8000` from another device on the network).

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and edit. All variables are optional; defaults use SQLite at `backend/data/portfolio.db` and sensible CORS for local Vite.

---

## Windows: install as a user app (Task Scheduler + log)

**From the repo:** build the frontend once, then run the installer (it copies `backend/` and `frontend/dist/` into your install directory):

```powershell
cd frontend
npm install
npm run build
cd ..\scripts
.\install-windows.ps1
```

**From a release package:** after `.\scripts\build-release.ps1`, open `release\DividendPortfolio` and follow `INSTALL.txt`, or run `.\install-windows.ps1` from that folder’s `scripts` subfolder.

Server logs when using `Run-Dashboard.ps1`: `%LOCALAPPDATA%\DividendPortfolio\logs\server.log` (default install path).

---

## iPhone alerts (ntfy)

1. Install [ntfy](https://ntfy.sh/) from the App Store.
2. Subscribe to a **unique**, hard-to-guess topic.
3. In the dashboard → **Alerty i ustawienia**, enter the same topic (and optional self-hosted ntfy URL).
4. Backend refreshes prices on a schedule and POSTs to ntfy when price ≤ average × (1 − threshold%). There is a **~6 h cooldown** per ticker to reduce spam.

---

## Tests

```powershell
cd backend
$env:SKIP_SCHEDULER = "1"   # PowerShell
python -m pytest tests -v
```

```bash
cd backend
export SKIP_SCHEDULER=1
python -m pytest tests -v
```

---

## Notes

- Yahoo data can be temporarily unavailable (network, rate limits); the UI may show "—" for a price.
- The stock universe is a starting set (PL / EU / US); you can extend it in code or via future tooling.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 blazejwrobel98.
