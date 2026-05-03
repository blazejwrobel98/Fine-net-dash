# Portfel dywidendowy (XTB — ręczne loty, ceny Yahoo)

Aplikacja webowa: lista spółek dywidendowych (50+), zapisywanie zakupów (także ułamkowych), średnia cena kupna, odświeżanie cen przez Yahoo Finance (`yfinance`), alerty gdy cena jest o wybrany procent poniżej średniej kupna.

## Wymagania

- Python 3.11+ (testowane na 3.13)
- Node.js 18+ (frontend)

## Backend

```powershell
cd backend
pip install -r requirements.txt
# opcjonalnie: $env:DATABASE_URL = "sqlite:///D:/sciezka/do/portfolio.db"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- API: `http://127.0.0.1:8000/api/...`
- Jeśli istnieje `frontend/dist`, ten sam serwer serwuje dashboard pod `/`.

Zmienna `SKIP_SCHEDULER=1` wyłącza harmonogram (np. testy).

## Frontend (development)

```powershell
cd frontend
npm install
npm run dev
```

Vite proxy: `/api` → `http://127.0.0.1:8000`.

## Frontend (produkcja w LAN)

```powershell
cd frontend
npm run build
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Wejdź z telefonu: `http://<IP-komputera>:8000`.

## Powiadomienia na iPhone (ntfy)

1. Zainstaluj aplikację [ntfy](https://ntfy.sh/) (App Store).
2. Wybierz „Subscribe to topic” i wpisz **unikalny**, trudny do zgadnięcia temat (np. losowy ciąg).
3. W dashboardzie → **Alerty i ustawienia** wpisz ten sam temat w polu „Temat ntfy”. Opcjonalnie zmień URL na własny serwer [self-hosted ntfy](https://docs.ntfy.sh/install/).
4. Włącz alerty i zapisz. Backend co N minut odświeża ceny i wysyła POST do ntfy, gdy cena ≤ średnia × (1 − próg% / 100). Między powiadomieniami dla tego samego tickera jest **cooldown ~6 h** (żeby nie spamować).

Alternatywy (wymagałyby dopisania integracji): Pushover, Telegram Bot, e-mail SMTP.

## Uwagi

- **XTB** nie jest podłączone — wpisujesz tylko to, co kupiłeś (ticker jak w Yahoo, np. `PZU.WA`, `KO`).
- Ceny z Yahoo bywają chwilowo niedostępne (sieć, limity); wtedy w UI zobaczysz „—” przy cenie.
- Lista spółek to punkt wyjścia (PL / EU / US); możesz rozszerzać bazę lub dodać endpoint edycji w przyszłości.

## Testy

```powershell
cd backend
$env:SKIP_SCHEDULER = "1"
python -m pytest tests -v
```
