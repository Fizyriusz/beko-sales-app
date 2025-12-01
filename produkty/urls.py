from django.urls import path
from . import views

app_name = 'produkty'  # Dodaj to, aby ustawić namespace dla aplikacji

urlpatterns = [
    path('produkty/', views.lista_produktow, name='lista_produktow'),
    path('', views.home, name='home'),
    path('import/', views.import_excel, name='import_excel'),
    path('test/', views.test_template, name='test_template'),
    path('sprzedaz/', views.sprzedaz, name='sprzedaz'),
    path('sprzedaz/sukces/', views.sprzedaz_sukces, name='sprzedaz_sukces'),
    path('podsumowanie/', views.podsumowanie_sprzedazy, name='podsumowanie_sprzedazy'),
    path('podsumowanie/reset/', views.reset_sprzedaz, name='reset_sprzedaz'),
    path('wyciagnij_liste_modeli/', views.wyciagnij_liste_modeli, name='wyciagnij_liste_modeli'),  # Nowy widok wyciągania listy modeli

    # Kalendarz
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/<int:year>/<int:month>/', views.calendar_view, name='calendar'),
    path('calendar/<int:year>/<int:month>/<int:day>/', views.daily_sales_view, name='daily_sales'),

    # Zadania
    path('zadania/', views.zadania_management, name='lista_zadan'),
    path('zadania/nowe/', views.zadanie_dodaj, name='nowe_zadanie'),
    path('zadania/edytuj/<int:zadanie_id>/', views.zadanie_edytuj, name='edytuj_zadanie'),
    path('zadania/usun/<int:zadanie_id>/', views.zadanie_usun, name='usun_zadanie'),
    path('zadania/<int:zadanie_id>/', views.szczegoly_zadania, name='szczegoly_zadania'),

    path('ekspozycja/<int:grupa_id>/', views.ekspozycja_form, name='ekspozycja_form'),
    path('ekspozycja-summary/', views.ekspozycja_summary, name='ekspozycja_summary'),
    path('ekspozycja-export/', views.eksportuj_ekspozycje_xlsx, name='ekspozycja_export'),
    path('klienci/', views.klienci, name='klienci'),
    path('klienci/zmien/<str:operacja>/', views.zmien_licznik, name='zmien_licznik'),
    path('import/delete-all/', views.delete_all_models, name='delete_all_models'),
    path('admin/delete-sales/', views.delete_sales_for_day, name='delete_sales_for_day'),
]