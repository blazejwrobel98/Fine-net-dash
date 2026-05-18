# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/). Wersje zgodne z tagami Git (`v*`).

## [Unreleased]

## [0.3.6] — 2026-05-18

- **Symulacje:** zakładka lookback (gdyby kupił wcześniej) i projekcja na przyszłość; API `/api/simulations/*`.
- **Cache symulacji:** zapis historii obliczeń, podgląd bez Yahoo, usuwanie (`/api/simulations/saved`).
- **Prognoza dywidend:** cache na serwerze, sync ilości z lotów, dzienny job odświeżania (6:15).
- **Lista spółek:** `localStorage` pamięta sortowanie, okres trendu (1D–5L), region i min. dywidendę.

## [0.3.5] — 2026-05-15

- **Wykresy:** wykres **wpłaty vs wartość portfela** — skumulowane wpłaty na konto (bez dywidend) obok wartości całkowitej; pole `deposits_cumulative_pln` w `/api/charts/timeline`.
- **Backend:** sprawdzanie aktualizacji — osobny cache odpowiedzi GitHub, `?refresh=1` na `/api/version/update`, krótszy TTL; domyślne **CORS** obejmuje porty **5174** i **IPv6 localhost** (`[::1]`).
- **Frontend:** baner aktualizacji i diagnostyka startu (timeout ładowania, `__FND_DEBUG__` w dev, pasek stanu bootu); pierwsze sprawdzenie wersji z odświeżeniem cache.

## [0.3.4] — 2026-05-11

- **Backend:** **`GET /api/version/update`** + schema **`UpdateCheckOut`** — informacja o nowszej wersji z GitHub Releases przez serwer (cache i obsługa błędów w `version_info.check_update_available`).
- **Frontend:** **favicon** (`public/favicon.svg`, link w `index.html`).
- **Frontend:** **zwijany panel boczny** na desktopie (tryb samych ikon), przycisk przy logo, stan w **`localStorage`** (`sidebarNavCollapsed`).

## [0.3.3] — 2026-05-09

- **Release:** workflow publikuje wyłącznie obraz Docker (**GHCR**); z CI usunięto ZIP, MSI oraz tarball Linux.
- **Dokumentacja:** [docs/Docker.md](docs/Docker.md) — `docker compose`, obraz z rejestru, `docker run`, przykładowy `compose` z `image:`, zmienne środowiskowe. Opis każdego release na GitHubie zawiera gotowy wiersz **`ghcr.io/.../fine-net-dash:<tag>`** do wklejenia w konfigurację.
- **Usunięto:** `packaging/windows` (WiX/MSI) oraz skrypty instalacji Windows/Linux (`build-release`, `install-windows`, MSI, tarball itd.).

## [0.3.2] — 2026-05-09

- **Zależności (zbieżnie z PR Dependabot 5–14):** frontend — Vite **8**, TypeScript **6**, `@vitejs/plugin-react` **5**; backend — `uvicorn` **0.46**, `sqlalchemy` **2.0.49**, `pydantic` **2.12.5**, `pydantic-settings` **2.14**, `python-multipart` **0.0.27**, `requests` **≥2.33.1**; CI / release — `actions/setup-node` **v6**.

## [0.3.1] — 2026-05-08

- **Kopie i przywracanie portfela:** przywracanie z UI przez **`sqlite3.Connection.backup`** (pełna zawartość pliku kopii), **`scheduler.pause()`** na czas operacji, **ponowienia** przy `database is locked`, zwalnianie poola SQLAlchemy (`engine.dispose()`), kopia źródłowa do pliku tymczasowego (stabilniej na Windows).
- **Lista kopii portfela:** pliki **`*before_restore*`** na **końcu** listy; w API i selectcie UI **liczba lotów**; sortowanie pod kątem przywrócenia; wyższa domyślna **retencja** kopii (`portfolio_backup_versions` = 15).
- **Windows instalacja:** `robocopy` z **`/XF portfolio.db`** (żeby nie nadpisywać bazy z drzewa źródłowego) oraz **`/IS` `/IT`**; po zatrzymaniu zadania harmonogramu — **zabicie** `python.exe` z venv instalacji przed kopiowaniem plików.
- **`scripts/restore-portfolio-db-file.ps1`:** podmiana całego `portfolio.db` offline; walidacja kopii przez tymczasowy skrypt Pythona (niezawodniej niż `python -c` w PowerShell); skrypt dołączany do wyjścia **`build-release`**.
- **`migrate_portfolio_db`:** bez **`--force`** nie modyfikuje celu, gdy SQLite zwraca nieczytelną bazę.
- Przy błędzie blokady przy przywracaniu z UI: komunikat z sugestią zatrzymania zadania harmonogramu lub użycia `restore-portfolio-db-file.ps1`.

## [0.3.0] — 2026-05-08

- **UI:** przebudowa interfejsu (shell 2026): sidebar na desktopie, dolna nawigacja na mobile, typografia Plus Jakarta Sans + JetBrains Mono.
- **UI:** tryb **ciemny / jasny** z zapisem w `localStorage` i wczesnym skryptem w `index.html` (mniej migania przy starcie).
- **UI:** toasty na błędy i komunikaty statusu zamiast dużych bloków na górze strony.
- **UI:** nawigacja z ikonami (**lucide-react**), spójne karty, tabele i siatka metryk w portfelu.
- **Wykresy:** kolory osi i datasetów dopasowane do aktywnego motywu (`chartTheme.ts` + prop `colorScheme` w `ChartsPanel`).
- **DX:** `package.json` w korzeniu repozytorium — `npm run dev` / `build` z głównego katalogu deleguje do `frontend/`.
- **UI:** wyrównanie przycisków z polami w poziomych rzędach (wyłączenie dolnego marginesu `.field` w `.row`).

## [0.2.3] — 2026-05-07

- Waluty tickerów Yahoo: poprawione mapowanie `.ST` -> `SEK` (np. `SWED-A.ST` nie jest już oznaczany jako `EUR`).
- Universe: dodane dwie kolumny dywidendy `%`:
  - **(poprz.)** — względem poprzedniej wypłaconej rocznej dywidendy (historyczna),
  - **(plan.)** — względem planowanej dywidendy rocznej (forward, gdy Yahoo zwraca `dividendRate`).
- Backend/API: nowe pole `dividend_yield_forward_pct` w cache cen, schemach i odpowiedzi `/api/universe`.
- Forward dywidendy: fallback parsowania `dividendRate` z HTML Yahoo, gdy endpoint quote zwraca puste dane / 429.
- Forward dywidendy: poprawka regexu dla danych osadzonych jako escaped JSON (`\"dividendRate\"`) na stronie Yahoo.
- Forward dywidendy: dodatkowy fallback na `trailingAnnualDividendRate`, gdy `dividendRate` (planowana) nie jest dostępna.
- UI Universe: sortowanie po kolumnie **Dywidenda % (plan.)**.
- UI Universe: usunięta kolumna **Notatka**.
- Ustawienia -> Kopie zapasowe: dodane **eksport** i **import** backupów (portfel `.db`, lista spółek `.json`).
- API backupów: nowe endpointy export/import dla portfela i listy spółek.
- UI Ustawień: sekcja kopii zapasowych przebudowana na bardziej kompaktowy, stabilny layout (bez rozjeżdżania przy mniejszej szerokości).
- UI Ustawień (iteracja): jeszcze ciaśniejszy layout backupów (mniejsze odstępy, mniejsze przyciski, krótszy opis).

## [0.2.2] — 2026-05-05

- Dywidenda `%`: liczona rocznie (ostatni rok kalendarzowy z wypłatą), zamiast rolling 12M.
- Alerty: poprawka porównania czasu (`naive`/`aware`) dla cooldownu w SQLite.
- Windows instalator: mocniejsze zabezpieczenie `portfolio.db` podczas aktualizacji (stop task + migawki awaryjne).

## [0.2.1] — 2026-05-04

- Docker: naprawa `HEALTHCHECK` — `CMD` zamiast niedozwolonego `CMD-SHELL` (buildx / `docker/dockerfile:1`).

## [0.2.0] — 2026-05-04

- **`GET /api/version`** + w banerze UI pole **„Build backendu”** (wersja + skrót SHA w obrazie z CI).
- Dokumentacja i komunikaty pod **pre-alfę** (README, baner w UI, zastrzeżenia prawne).
- Bezpieczeństwo: domyślnie wyłączone `/docs` / OpenAPI (`ENABLE_OPENAPI=1` włącza), nagłówki HTTP, opcjonalne `TRUSTED_HOSTS`.
- Jakość: `datetime` w UTC (timezone-aware), `npm audit fix`, czytelniejsze błędy API w UI.
- Docker: proces nieuprzywilejowany (`app`), healthcheck z `PORT`.
- Windows: `Dokoncz-instalacje-msi.bat` po instalacji MSI; przed `robocopy` w `install-windows.ps1` kopia zapasowa `portfolio.db.preinstall-*`.
- Community: `SECURITY.md`, `CONTRIBUTING.md`, Dependabot (npm + pip).

## [0.1.2] — 2026-05-03

- CI: przypięcie WiX **6.0.2** (uniknięcie wymogu OSMF EULA WiX 7).

## [0.1.1] — 2026-05-03

- CI: `exit 0` po `robocopy` w skryptach release (poprawny kod wyjścia na Windows).

## [0.1.0] — 2026-05-03

- Pierwszy tag release: Docker (GHCR), tarball Linux, ZIP + MSI Windows, GitHub Actions.
