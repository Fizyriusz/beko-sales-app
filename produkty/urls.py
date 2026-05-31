from django.urls import path
from . import views

app_name = 'produkty'  # Dodaj to, aby ustawić namespace dla aplikacji

urlpatterns = [
    path('produkty/', views.lista_produktow, name='lista_produktow'),
    path('produkty/edit/<int:product_id>/', views.product_edit, name='product_edit'),
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
    path('zadania/', views.zadania_management, name='zadania_management'),
    path('zadania/<int:year>/<int:month>/', views.zadania_view, name='zadania_view'),
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
    
    # Otwarcie/Zamkniecie dnia
    path('dzien/otwarcie/', views.otwarcie_dnia, name='otwarcie_dnia'),
    path('dzien/zamkniecie/', views.zamkniecie_dnia, name='zamkniecie_dnia'),
    path('dzien/checklista/', views.checklista_podglad, name='checklista_podglad'),
    
    # Grafik
    path('grafik/', views.grafik_view, name='grafik'),
    path('grafik/import/', views.import_grafiku, name='import_grafiku'),

    # Hub Wiedzy
    path('hub-wiedzy/', views.hub_wiedzy, name='hub_wiedzy'),
    path('hub-wiedzy/funkcja/dodaj/', views.funkcja_dodaj, name='funkcja_dodaj'),
    path('hub-wiedzy/funkcja/<int:funkcja_id>/', views.funkcja_szczegoly, name='funkcja_szczegoly'),
    path('hub-wiedzy/funkcja/edytuj/<int:funkcja_id>/', views.funkcja_edytuj, name='funkcja_edytuj'),
    path('hub-wiedzy/podpowiedz/dodaj/', views.podpowiedz_dodaj, name='podpowiedz_dodaj'),
    path('hub-wiedzy/podpowiedz/<int:podpowiedz_id>/', views.podpowiedz_szczegoly, name='podpowiedz_szczegoly'),
    path('hub-wiedzy/podpowiedz/edytuj/<int:podpowiedz_id>/', views.podpowiedz_edytuj, name='podpowiedz_edytuj'),
    
    # Historia Sprzedazy
    path('produkt/<int:produkt_id>/historia/', views.historia_sprzedazy_produktu, name='historia_sprzedazy_produktu'),

    # Konta
    path('konta/', views.konta_lista, name='konta_lista'),
    path('konta/dodaj/', views.konto_dodaj, name='konto_dodaj'),
    path('konta/edytuj/<int:user_id>/', views.konto_edytuj, name='konto_edytuj'),
    path('konta/usun/<int:user_id>/', views.konto_usun, name='konto_usun'),

    # Lista TOP
    path('top-lista/', views.top_lista, name='top_lista'),
    path('top-lista/zapisz/<int:subgrupa_id>/', views.top_lista_zapisz, name='top_lista_zapisz'),
    path('top-lista/manage/', views.top_lista_manage, name='top_lista_manage'),
    path('top-lista/manage/group/add/', views.top_lista_group_add, name='top_lista_group_add'),
    path('top-lista/manage/subgroup/add/', views.top_lista_subgroup_add, name='top_lista_subgroup_add'),
    path('top-lista/manage/group/delete/<int:group_id>/', views.top_lista_delete_group, name='top_lista_delete_group'),
    path('top-lista/manage/subgroup/delete/<int:subgroup_id>/', views.top_lista_delete_subgroup, name='top_lista_delete_subgroup'),
]