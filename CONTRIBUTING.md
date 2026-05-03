# Wkład w projekt

Dzięki za zainteresowanie **Fine Net Dash** (wersja robocza / pre-alfa).

## Zgłoszenia

- **Błędy i pomysły:** [Issues](https://github.com/blazejwrobel98/Fine-net-dash/issues) na GitHubie.  
- **Bezpieczeństwo:** [SECURITY.md](SECURITY.md).

## Środowisko

1. **Backend:** Python 3.11+, `cd backend && pip install -r requirements.txt`  
2. **Frontend:** Node 18+, `cd frontend && npm install`  
3. Testy backendu: `SKIP_SCHEDULER=1 pytest backend/tests -v` (z katalogu `backend`).  
4. Build frontu: `npm run build` w `frontend`.

## Pull requesty

- Jedna logiczna zmiana na PR, opis po polsku lub angielsku — jasno napisz **co** i **dlaczego**.  
- Upewnij się, że `pytest` i `npm run build` przechodzą lokalnie.  
- Nie commituj plików `.env`, baz `*.db`, `node_modules/`, `frontend/dist/`.

## Styl

Dopasuj się do istniejącego stylu pliku (formatowanie, nazewnictwo). Unikaj rozległych refaktorów „przy okazji”.
