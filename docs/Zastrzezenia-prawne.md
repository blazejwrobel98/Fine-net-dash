# Zastrzeżenia prawne (Fine Net Dash / portfel dywidendowy)

Ostatnia aktualizacja: maj 2026. Aplikacja jest w **wczesnej fazie rozwoju (pre-alfa)**; treść może się zmieniać.

## To nie jest porada inwestycyjna

Program służy wyłącznie do **własnej organizacji informacji** o transakcjach i danych rynkowych, które samodzielnie wprowadzasz lub które są pobierane z zewnętrznych źródeł. **Nie stanowi rekomendacji zakupu ani sprzedaży papierów wartościowych**, doradztwa finansowego, podatkowego ani prawnego. Decyzje inwestycyjne podejmujesz wyłącznie na własną odpowiedzialność.

## Źródła danych zewnętrznych

- **Ceny i metryki rynkowe** mogą pochodzić z ekosystemu Yahoo Finance (w tym biblioteki `yfinance`). Dane mogą być **niekompletne, opóźnione lub błędne**. Korzystanie z Yahoo i powiązanych usług podlega **ich regulaminom i politykom** — użytkownik instalujący aplikację akceptuje, że to on odpowiada za legalność użycia danych w swoim środowisku.
- **Kursy USD/EUR z NBP** pochodzą z publicznych interfejsów NBP; mogą wystąpić przerwy w dostępie lub błędy sieciowe.
- **Powiadomienia ntfy** wysyłane są na adres URL i temat skonfigurowany przez użytkownika; odpowiadasz za wybór bezpiecznego tematu i ewentualnie własnego serwera.

## Czcionki (frontend)

Interfejs może ładować czcionki z **Google Fonts** (żądanie do serwerów Google). Przy hostowaniu lokalnym adres IP może być przekazany do dostawcy czcionek zgodnie z ich polityką.

## Oprogramowanie i licencja

Kod aplikacji udostępniany jest na zasadach licencji w repozytorium (np. **MIT**), **„tak jak jest” (as-is)**, bez gwarancji przydatności handlowej lub nie naruszania praw osób trzecich.

## Brak centralnego hostingu przez autorów

Domyślny model użycia to **instalacja u Ciebie** (komputer, Docker, własna sieć). **Nie prowadzimy centralnej usługi chmurowej** przetwarzającej Twój portfel w imieniu projektu — w tej konfiguracji **nie udostępniamy osobnej polityki prywatności SaaS**. Dane portfela zapisujesz lokalnie (np. SQLite), chyba że sam skonfigurujesz inne środowisko.

## Kontakt w sprawach prawnych / błędów

Prosimy o zgłoszenia przez **Issues na GitHubie** wskazanego repozytorium projektu (nie gwarantujemy indywidualnej odpowiedzi prawnej).
