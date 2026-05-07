# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/). Wersje zgodne z tagami Git (`v*`).

## [Unreleased]

- Przywracanie portfela z kopii (`/api/backups/portfolio/restore`): kopiowane są też **universe_stocks**, **price_cache**, **app_settings**, **alert_cooldowns** (wcześniej tylko loty / sprzedaże / wpłaty / dywidendy / snapshoty — brak „spółek” w cache i ustawień).
- Przy błędzie blokady SQLite komunikat z sugestią zatrzymania zadania harmonogramu lub użycia skryptu `scripts/restore-portfolio-db-file.ps1`.
- Nowy skrypt **`scripts/restore-portfolio-db-file.ps1`**: podmiana całego `portfolio.db` z pobranej kopii przy wyłączonym serwerze (najpewniejsze przy „database is locked”).
- Przywracanie portfela z UI: przed `ATTACH` zwalniany jest **pool SQLAlchemy** (`engine.dispose()`), kopia źródłowa jest **kopiowana do pliku tymczasowego** (unika błędu `database srcdb is locked` na Windows), zwiększony **timeout** połączenia do głównej bazy.
- Przywracanie portfela: kopiowanie wierszy po **wspólnej liście kolumn** (zamiast `SELECT *`), żeby starsze kopie SQLite nie wywalały błędu typu „N kolumn ale M wartości” przy nowszym schemacie (np. `price_cache`).
- Przywracanie portfela z UI: **`scheduler.pause()`** na czas operacji (zwalnia joby odświeżania cen), **ponowienia** przy `database is locked` (~12 s), usuwanie pliku roboczego `.restore-work-*.db` w `finally`.
- Lista kopii portfela: pliki **`*before_restore*`** trafiają **na koniec** listy (wcześniej były zawsze najnowsze i lądowały jako domyślny wybór w UI — łatwo było „przywrócić” właśnie złą, świeżą kopię zamiast pobranej dobrej). UI + krótka podpowiedź w ustawieniach.

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
