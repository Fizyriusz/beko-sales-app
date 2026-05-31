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

from .models import PunktChecklisty, DzienPracy, OdpowiedzChecklisty, GrafikPracy

@admin.register(PunktChecklisty)
class PunktChecklistyAdmin(admin.ModelAdmin):
    list_display = ('tekst', 'aktywny', 'kolejnosc')
    list_editable = ('aktywny', 'kolejnosc')
    ordering = ('kolejnosc',)

@admin.register(GrafikPracy)
class GrafikPracyAdmin(admin.ModelAdmin):
    list_display = ('user', 'data', 'godzina_rozpoczecia', 'godzina_zakonczenia', 'suma_godzin')
    list_filter = ('data', 'user')
    date_hierarchy = 'data'

admin.site.register(DzienPracy)
admin.site.register(OdpowiedzChecklisty)

from .models import Funkcja, Podpowiedz

@admin.register(Funkcja)
class FunkcjaAdmin(admin.ModelAdmin):
    list_display = ('nazwa',)
    filter_horizontal = ('produkty',)

admin.site.register(Podpowiedz)

from .models import TopGroup, TopSubGroup, TopListEntry
admin.site.register(TopGroup)
admin.site.register(TopSubGroup)
admin.site.register(TopListEntry)