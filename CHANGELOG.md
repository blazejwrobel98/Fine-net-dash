# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/). Wersje zgodne z tagami Git (`v*`).

## [Unreleased]

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
