# Bezpieczeństwo

## Zgłaszanie podatności

Na ten moment prosimy o zgłoszenia **wyłącznie przez [Issues](https://github.com/blazejwrobel98/Fine-net-dash/issues)** w tym repozytorium (tytuł z prefiksem `[security]` lub opis w treści).

Nie udostępniamy osobnego formularza e-mail ani bug bounty. Jeśli zgłoszenie zawiera wrażliwe szczegóły exploitacji, **nie publikuj ich wprost w publicznym issue** — opisz ogólnie wektor ataku; szczegóły można podać po kontakcie z maintainerem repozytorium (np. przez GitHub).

## Model zagrożeń

Aplikacja jest przeznaczona głównie do **lokalnego / zaufanego** użycia. API **nie implementuje uwierzytelniania użytkownika** — zakładamy, że dostęp do sieci i portu ma tylko zaufany podmiot.

## Zalecenia przy hostowaniu

- Nie wystawiaj portu backendu publicznie bez reverse proxy, TLS i ograniczenia dostępu (firewall / VPN).  
- Rozważ ustawienie `TRUSTED_HOSTS` w `.env`, jeśli używasz domeny za reverse proxy.  
- Domyślnie dokumentacja OpenAPI jest wyłączona; nie włączaj `ENABLE_OPENAPI=1` na produkcji bez potrzeby.
