# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/). Wersje zgodne z tagami Git (`v*`).

## [Unreleased]

- Waluty tickerów Yahoo: poprawione mapowanie `.ST` -> `SEK` (np. `SWED-A.ST` nie jest już oznaczany jako `EUR`).
- Universe: dodane dwie kolumny dywidendy `%`:
  - **(poprz.)** — względem poprzedniej wypłaconej rocznej dywidendy (historyczna),
  - **(plan.)** — względem planowanej dywidendy rocznej (forward, gdy Yahoo zwraca `dividendRate`).
- Backend/API: nowe pole `dividend_yield_forward_pct` w cache cen, schemach i odpowiedzi `/api/universe`.
- Forward dywidendy: fallback parsowania `dividendRate` z HTML Yahoo, gdy endpoint quote zwraca puste dane / 429.
- Forward dywidendy: poprawka regexu dla danych osadzonych jako escaped JSON (`\"dividendRate\"`) na stronie Yahoo.

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
