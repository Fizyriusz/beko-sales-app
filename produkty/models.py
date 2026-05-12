from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Produkt(models.Model):
    model = models.CharField(max_length=100, unique=True)
    stawka = models.DecimalField(max_digits=10, decimal_places=2)
    grupa_towarowa = models.CharField(max_length=100)
    marka = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.model

class Zadanie(models.Model):
    nazwa = models.CharField(max_length=255)
    opis = models.TextField(blank=True)
    produkty = models.ManyToManyField('Produkt', related_name='zadania', blank=True)
    data_start = models.DateField()
    data_koniec = models.DateField()
    target = models.CharField(max_length=10, choices=[('ilosc', 'Ilość'), ('wartosc', 'Wartość')], default='ilosc')
    prog_1 = models.PositiveIntegerField(null=True, blank=True)
    prog_1_premia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prog_2 = models.PositiveIntegerField(null=True, blank=True)
    prog_2_premia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mnoznik_mix = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Mnożnik dla zadań typu mix")
    prog_mix = models.PositiveIntegerField(null=True, blank=True, help_text="Próg dla zadań typu mix")
    typ = models.CharField(
        max_length=20,
        choices=[
            ("MIX_PROWIZJA", "Mix prowizja"),
            ("MIX_MNOZNIK", "Mix mnożnik"),
            ("KONKRETNE_MODELE", "Konkretne modele"),
        ],
        default="KONKRETNE_MODELE",
    )

    def __str__(self):
        return f"{self.nazwa} ({self.data_start} - {self.data_koniec})"


class Sprzedaz(models.Model):
    produkt = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    liczba_sztuk = models.IntegerField()
    data_sprzedazy = models.DateField(default=date.today)
    zadanie = models.ForeignKey(Zadanie, on_delete=models.SET_NULL, null=True, blank=True)
    prowizja = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.produkt.model} - {self.liczba_sztuk} sztuk - {self.data_sprzedazy} - prowizja: {self.prowizja}"

class GrupaProduktowa(models.Model):
    nazwa = models.CharField(max_length=100)

    def __str__(self):
        return self.nazwa

class Marka(models.Model):
    nazwa = models.CharField(max_length=100)

    def __str__(self):
        return self.nazwa

class Ekspozycja(models.Model):
    grupa = models.ForeignKey(GrupaProduktowa, on_delete=models.CASCADE)
    marka = models.ForeignKey(Marka, on_delete=models.CASCADE)
    liczba = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.grupa.nazwa} - {self.marka.nazwa}: {self.liczba}"

class KlientCounter(models.Model):
    data = models.DateField(default=date.today)
    liczba_klientow = models.IntegerField(default=0)
    notatka = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Licznik klientów z dnia {self.data}: {self.liczba_klientow}"

class PunktChecklisty(models.Model):
    tekst = models.TextField()
    aktywny = models.BooleanField(default=True)
    kolejnosc = models.IntegerField(default=0)

    class Meta:
        ordering = ['kolejnosc']

    def __str__(self):
        return self.tekst[:50]

class DzienPracy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField(default=date.today)
    czas_otwarcia = models.DateTimeField(auto_now_add=True)
    czas_zamkniecia = models.DateTimeField(null=True, blank=True)
    notatka_sprzedaz = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'data')

    def __str__(self):
        return f"{self.user.username} - {self.data}"

class OdpowiedzChecklisty(models.Model):
    dzien_pracy = models.ForeignKey(DzienPracy, on_delete=models.CASCADE, related_name='odpowiedzi_checklisty')
    punkt = models.ForeignKey(PunktChecklisty, on_delete=models.CASCADE)
    wykonano = models.BooleanField(default=False)

    class Meta:
        unique_together = ('dzien_pracy', 'punkt')

    def __str__(self):
        return f"{self.dzien_pracy} - {self.punkt}: {self.wykonano}"

class GrafikPracy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField()
    godzina_rozpoczecia = models.TimeField(null=True, blank=True)
    godzina_zakonczenia = models.TimeField(null=True, blank=True)
    suma_godzin = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notatka = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'data')
        ordering = ['-data']

    def __str__(self):
        return f"{self.user.username} - {self.data}"