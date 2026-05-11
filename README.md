# Fine Net Dash — portfel dywidendowy

**Wersja robocza (pre-alfa).** Aplikacja webowa do ręcznego prowadzenia portfela dywidendowego: lista spółek, loty (także ułamkowe), średnia cena kupna, ceny z Yahoo Finance (`yfinance`), opcjonalne alerty ntfy.

Repozytorium: [github.com/blazejwrobel98/Fine-net-dash](https://github.com/blazejwrobel98/Fine-net-dash)  
Licencja: [MIT](LICENSE) — bez gwarancji.

Interfejs użytkownika jest **po polsku**. Krótkie zastrzeżenia prawne: [docs/Zastrzezenia-prawne.md](docs/Zastrzezenia-prawne.md).

---

## Dla kogo i jak wdrażamy

Projekt jest pisany z myślą o **samodzielnej instalacji u siebie** (komputer domowy, Docker na własnym hoście, sieć lokalna). **Na ten moment zalecamy wyłącznie lokalne lub zaufane wdrożenia** — nie hostuj publicznie w otwartym internecie bez dodatkowej warstwy zabezpieczeń (reverse proxy, firewall, VPN), o ile w ogóle.

**Nie prowadzimy centralnego SaaS** — nie zbieramy Twojego portfela po stronie serwera projektu; dane siedzą u Ciebie (np. plik SQLite). Dlatego **nie publikujemy osobnej polityki prywatności usługi chmurowej** — patrz też [Zastrzezenia prawne](docs/Zastrzezenia-prawne.md).

---

## Bezpieczeństwo (ważne)

- **API nie ma logowania użytkownika** — każdy, kto ma sieciowy dostęp do adresu backendu, może wykonywać operacje API. Traktuj instalację jak narzędzie **tylko dla siebie** lub w sieci, którą kontrolujesz.
- **`GET /api/version`** — zwraca numer wersji i opcjonalnie skrót SHA buildu (w Dockerze z CI ustawiane przez `APP_VERSION` / `GIT_SHA`). W UI (żółty pasek u góry) widać **„Build backendu”**, żeby nie mylić starej instalacji z nową.
- Domyślnie **wyłączone są** strony dokumentacji OpenAPI (`/docs`, `/redoc`, `/openapi.json`). Włączenie: zmienna środowiskowa `ENABLE_OPENAPI=1` (np. przy debugowaniu).
- Do odpowiedzi dodawane są podstawowe **nagłówki bezpieczeństwa** (m.in. `X-Frame-Options`, `X-Content-Type-Options`).
- Opcjonalnie: **`TRUSTED_HOSTS`** — lista hostów po przecinku (np. za reverse proxy); puste = wyłączone.

Zgłaszanie problemów bezpieczeństwa: [SECURITY.md](SECURITY.md).

---

## Wymagania

| Składnik  | Wersja        |
| ---------- | ------------- |
| Python     | 3.11+         |
| Node.js    | 18+ (tylko build frontu) |

XTB **nie jest podłączone** — wpisujesz tickery jak w Yahoo (np. `PZU.WA`, `KO`).

---

## Uruchomienie deweloperskie (dwa procesy)

**Backend** (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # opcjonalnie
$env:ENABLE_OPENAPI = "1"   # opcjonalnie: włącz /docs
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend** (drugi terminal):

```powershell
cd frontend
npm install
npm run dev
```

Aplikacja w przeglądarce: **http://127.0.0.1:5173** (proxy `/api` → port 8000).

**Linux/macOS:** analogicznie z `python3 -m venv` i `source .venv/bin/activate`.

---

## Jedna usługa (build frontu + backend)

```bash
cd frontend && npm install && npm run build
cd ../backend
# aktywuj venv
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Dashboard: `http://127.0.0.1:8000/`.

---

## Docker (zalecane do uruchomienia „u siebie”)

Pełna instrukcja: **[docs/Docker.md](docs/Docker.md)** — `docker compose` z kodu, **gotowy obraz GHCR**, przykładowe `docker run` / fragment `compose` tylko z `image:`, zmienne środowiskowe i healthcheck.

Skrót z repozytorium (build lokalny):

```bash
docker compose up --build
```

Aplikacja: **http://127.0.0.1:8000/**. Obraz działa jako użytkownik nieuprzywilejowany (`app`); dane SQLite są w wolumenie (`/app/backend/data` w kontenerze).

---

## Wydania (GitHub Releases + GHCR)

Po wypchnięciu tagu **`v*`** (np. `v0.3.3`) CI publikuje obraz i stronę wydania.

| Dostawa | Opis |
| ------- | ----- |
| **Obraz kontenera** | `ghcr.io/blazejwrobel98/fine-net-dash:<tag>` — `<tag>` taki sam jak tag na GitHubie (np. `v0.3.3`); dodatkowo tag **`latest`**. |

W opisie każdego release na GitHubie jest **gotowy wiersz `image:`** do skopiowania. Szczegóły uruchomienia: [docs/Docker.md](docs/Docker.md).

---

## Konfiguracja (`backend/.env`)

Skopiuj `backend/.env.example` → `backend/.env`. Dla testów CI / pytest: `SKIP_SCHEDULER=1`.

---

## Powiadomienia (ntfy, iPhone)

1. Aplikacja [ntfy](https://ntfy.sh/) z App Store.  
2. Unikalny, trudny temat subskrypcji.  
3. W aplikacji → **Alerty i ustawienia** — ten sam temat (opcjonalnie własny serwer ntfy).  
4. Backend okresowo odświeża ceny; przy spełnionym progu wysyła POST do ntfy. **Cooldown ~6 h** na ticker.

---

## Testy

```powershell
cd backend
$env:SKIP_SCHEDULER = "1"
python -m pytest tests -v
```

Frontend: `npm run build` w katalogu `frontend` (uruchamiane w CI).

---

## Wkład i zgłoszenia

- Wkład w kod: [CONTRIBUTING.md](CONTRIBUTING.md)  
- Błędy i pomysły: **Issues** w tym repozytorium  
- Bezpieczeństwo: [SECURITY.md](SECURITY.md)

---

## Uwagi techniczne

- Dane Yahoo bywają chwilowo niedostępne — w UI może pojawić się „—”.  
- Lista spółek to punkt wyjścia; możesz ją rozszerzać w kodzie.

---

## Historia wersji

Skrót zmian: [CHANGELOG.md](CHANGELOG.md). Szczegóły buildów: [GitHub Releases](https://github.com/blazejwrobel98/Fine-net-dash/releases).
