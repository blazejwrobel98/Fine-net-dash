# Uruchomienie w kontenerze (Docker)

Aplikacja to jeden obraz: backend **FastAPI** serwuje zbudowany frontend ze `frontend/dist`. Dane portfela to plik **SQLite** w wolumenie (ścieżka w kontenerze: `/app/backend/data`).

## Wymagania

- [Docker](https://docs.docker.com/get-docker/) (Engine + `docker compose` v2).

## Z kodu źródłowego (lokalnie)

Z katalogu głównego repozytorium:

```bash
docker compose up --build
```

Dashboard: **http://127.0.0.1:8000/**. Dane są w wolumenie Dockera `appdata` (nazwa z `docker-compose.yml`).

Zatrzymanie: `Ctrl+C` albo `docker compose down` (wolumen z bazą zostaje; żeby go skasować: `docker compose down -v`).

## Gotowy obraz z GitHub Container Registry (GHCR)

Po [wydaniu (tag `v*`)](https://github.com/blazejwrobel98/Fine-net-dash/releases) CI buduje i wypycha obraz. **Skopiuj dokładnie ten wiersz** do swojej konfiguracji (`image:` w Compose, w panelu hosta itd.):

```text
ghcr.io/blazejwrobel98/fine-net-dash:<TAG>
```

Zastąp `<TAG>` numerem wydania, np. `v0.3.3` (taki sam ciąg jak tag na GitHubie). Dostępny jest też tag **`latest`** — wskazuje na ostatni zbudowany release z tagiem `v*`.

Przykład **jednorazowego** uruchomienia (port 8000, baza w nazwanym wolumenie):

```bash
docker pull ghcr.io/blazejwrobel98/fine-net-dash:v0.3.3
docker volume create fine-net-dash-data
docker run -d --name fine-net-dash \
  -p 8000:8000 \
  -v fine-net-dash-data:/app/backend/data \
  -e DATABASE_URL=sqlite:////app/backend/data/portfolio.db \
  --restart unless-stopped \
  ghcr.io/blazejwrobel98/fine-net-dash:v0.3.3
```

### Przykładowy `docker-compose` tylko z rejestru

```yaml
services:
  web:
    image: ghcr.io/blazejwrobel98/fine-net-dash:v0.3.3
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: sqlite:////app/backend/data/portfolio.db
    volumes:
      - appdata:/app/backend/data
    restart: unless-stopped

volumes:
  appdata:
```

Podmień `v0.3.3` na właściwy tag z [Releases](https://github.com/blazejwrobel98/Fine-net-dash/releases).

## Zmienne środowiskowe (wybrane)

| Zmienna | Opis |
| -------- | ----- |
| `DATABASE_URL` | Domyślnie SQLite pod `/app/backend/data`; w compose ustaw jak wyżej. |
| `SKIP_SCHEDULER` | `1` — wyłącza harmonogram odświeżania (np. testy). |
| `ENABLE_OPENAPI` | `1` — włącza `/docs`, `/redoc`. |
| `APP_VERSION` / `GIT_SHA` | Ustawiane przy buildzie w CI; lokalnie możesz nadpisać. |

Pełna lista: `backend/.env.example`.

## Bezpieczeństwo

API **nie ma logowania** — nie wystawiaj portu publicznie bez reverse proxy, firewalla lub VPN. Zobacz też [README — bezpieczeństwo](../README.md#bezpieczeństwo-ważne).

## Healthcheck

Obraz ma `HEALTHCHECK` na `GET /api/health`. Sprawdzenie: `docker inspect --format='{{.State.Health.Status}}' fine-net-dash`.
