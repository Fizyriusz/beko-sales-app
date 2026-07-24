# Beko Sales App

Aplikacja webowa (Django 5) do zarządzania sprzedażą i prowizjami sprzedawców
sprzętu AGD. Umożliwia codzienne wpisywanie sprzedanych modeli, liczenie
prowizji, obsługę zadań premiowych, ekspozycji, grafiku pracy, checklisty dnia
oraz hubu wiedzy o produktach.

## Stack

- **Backend:** Python + Django 5.1
- **Baza danych:** PostgreSQL (produkcja), SQLite (lokalnie / testy)
- **Serwer:** Gunicorn + WhiteNoise (pliki statyczne)
- **Dodatkowo:** openpyxl (import/eksport Excel), RapidFuzz (dopasowanie modeli)

## Struktura projektu

```
beko_project/        # Konfiguracja projektu Django (settings, urls, wsgi/asgi)
produkty/            # Główna aplikacja domenowa
  models.py          # Modele danych (produkty, sprzedaż, zadania, grafik, ...)
  views.py           # Logika biznesowa i widoki
  forms.py           # Formularze
  urls.py            # Trasy aplikacji
  templates/         # Szablony HTML
  static/            # CSS + JS
  templatetags/      # Własne filtry szablonów
  migrations/        # Migracje bazy danych
manage.py            # Punkt wejścia Django
build.sh             # Skrypt build/deploy (install + collectstatic + migrate)
requirements.txt     # Zależności Pythona
```

## Uruchomienie lokalne

```bash
python -m venv env
source env/bin/activate      # Windows: env\Scripts\activate
pip install -r requirements.txt
```

Utwórz plik `.env` w katalogu głównym:

```
DEBUG=True
SECRET_KEY=dowolny-lokalny-klucz
ALLOWED_HOSTS=localhost,127.0.0.1
# DATABASE_URL jest opcjonalny lokalnie - przy DEBUG=True używany jest SQLite
```

Migracje i start serwera:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Zmienne środowiskowe

| Zmienna | Wymagana | Opis |
|---------|----------|------|
| `SECRET_KEY` | tak w produkcji | Klucz kryptograficzny Django. Przy `DEBUG=True` lub w testach ma bezpieczny fallback deweloperski. |
| `DEBUG` | nie | `True`/`False` (domyślnie `False`). |
| `ALLOWED_HOSTS` | tak w produkcji | Lista hostów rozdzielona przecinkami. |
| `DATABASE_URL` | tak w produkcji | URL bazy (np. PostgreSQL). Lokalnie/testowo fallback na SQLite. |

## Testy

```bash
python manage.py test
```

Testy używają bazy SQLite w pamięci (nie wymagają `DATABASE_URL`).

## Deploy

`build.sh` instaluje zależności, zbiera pliki statyczne i uruchamia migracje —
przeznaczony pod platformy typu Render. W produkcji ustaw wszystkie wymagane
zmienne środowiskowe i `DEBUG=False`.
