from django.contrib import admin
from .models import Produkt, Sprzedaz, Zadanie, GrupaProduktowa, Marka, Ekspozycja
from .forms import ZadanieForm

# Rejestracja modelu Produkt w panelu admina
admin.site.register(Produkt)

# Rejestracja modelu Sprzedaz w panelu admina
admin.site.register(Sprzedaz)

# Rejestracja modelu Zadanie z niestandardowym formularzem w panelu admina
@admin.register(Zadanie)
class ZadanieAdmin(admin.ModelAdmin):
    form = ZadanieForm
    list_display = ('nazwa', 'data_start', 'data_koniec', 'prog_1', 'prog_1_premia', 'prog_2', 'prog_2_premia')
    search_fields = ('nazwa',)
    list_filter = ('data_start', 'data_koniec',)
    filter_horizontal = ('produkty',)

admin.site.register(GrupaProduktowa)
admin.site.register(Marka)
admin.site.register(Ekspozycja)