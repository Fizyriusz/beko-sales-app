from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Produkt(models.Model):
    model = models.CharField(max_length=100, unique=True)
    stawka = models.DecimalField(max_digits=10, decimal_places=2)
    grupa_towarowa = models.CharField(max_length=100)
    marka = models.CharField(max_length=100, null=True, blank=True)
    data_aktualizacji = models.DateField(null=True, blank=True, verbose_name="Data ostatniej aktualizacji")

    def __str__(self):
        return self.model

class Zadanie(models.Model):
    class Typ(models.TextChoices):
        MIX_PROWIZJA = "MIX_PROWIZJA", "Mix prowizja"
        MIX_MNOZNIK = "MIX_MNOZNIK", "Mix mnożnik"
        KONKRETNE_MODELE = "KONKRETNE_MODELE", "Konkretne modele"

    nazwa = models.CharField(max_length=255)
    opis = models.TextField(blank=True)
    produkty = models.ManyToManyField('Produkt', related_name='zadania', blank=True)
    data_start = models.DateField()
    data_koniec = models.DateField()
    target = models.CharField(max_length=10, choices=[('ilosc', 'Ilość'), ('wartosc', 'Wartość')], default='ilosc', blank=True)
    prog_1 = models.PositiveIntegerField(null=True, blank=True)
    prog_1_premia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prog_2 = models.PositiveIntegerField(null=True, blank=True)
    prog_2_premia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mnoznik_mix = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Mnożnik dla zadań typu mix")
    prog_mix = models.PositiveIntegerField(null=True, blank=True, help_text="Próg dla zadań typu mix")
    typ = models.CharField(
        max_length=20,
        choices=Typ.choices,
        default=Typ.KONKRETNE_MODELE,
        blank=True
    )

    def __str__(self):
        return f"{self.nazwa} ({self.data_start} - {self.data_koniec})"


class Sprzedaz(models.Model):
    produkt = models.ForeignKey(Produkt, on_delete=models.CASCADE)
    liczba_sztuk = models.IntegerField()
    data_sprzedazy = models.DateField(default=date.today)
    zadanie = models.ForeignKey(Zadanie, on_delete=models.SET_NULL, null=True, blank=True)
    prowizja = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Kto zaraportowal sprzedaz - potrzebne do rozliczania targetow hal.
    # Puste dla sprzedazy sprzed wprowadzenia hal (mozna przypisac hurtowo).
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sprzedaze', verbose_name="Sprzedawca",
    )

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

class Funkcja(models.Model):
    nazwa = models.CharField(max_length=255)
    opis = models.TextField(blank=True, null=True)
    produkty = models.ManyToManyField(Produkt, related_name='funkcje', blank=True)

    def __str__(self):
        return self.nazwa

class Podpowiedz(models.Model):
    tytul = models.CharField(max_length=255)
    tresc = models.TextField()

    def __str__(self):
        return self.tytul

class TopGroup(models.Model):
    nazwa = models.CharField(max_length=150, verbose_name="Nazwa grupy")
    aktywna = models.BooleanField(default=True, verbose_name="Aktywna")
    kolejnosc = models.IntegerField(default=0, verbose_name="Kolejność")

    class Meta:
        ordering = ['kolejnosc', 'nazwa']

    def __str__(self):
        return self.nazwa

class TopSubGroup(models.Model):
    grupa = models.ForeignKey(TopGroup, on_delete=models.CASCADE, related_name='subgrupy')
    nazwa = models.CharField(max_length=150, verbose_name="Nazwa podgrupy")
    kolejnosc = models.IntegerField(default=0, verbose_name="Kolejność")

    class Meta:
        ordering = ['kolejnosc', 'nazwa']

    def __str__(self):
        return f"{self.grupa.nazwa} - {self.nazwa}"

class TopListEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='top_listy')
    subgrupa = models.ForeignKey(TopSubGroup, on_delete=models.CASCADE, related_name='wpisy')
    pozycja = models.PositiveIntegerField(verbose_name="Pozycja")
    model_tekst = models.CharField(max_length=150, verbose_name="Model")

    class Meta:
        ordering = ['pozycja']
        unique_together = ('user', 'subgrupa', 'pozycja')

    def __str__(self):
        return f"{self.user.username} - {self.subgrupa} - #{self.pozycja}: {self.model_tekst}"


class Alejka(models.Model):
    """Alejka w markecie - element mapy z lotu ptaka."""
    class Orientacja(models.TextChoices):
        PIONOWA = "V", "Pionowa"
        POZIOMA = "H", "Pozioma"

    nazwa = models.CharField(max_length=150, verbose_name="Nazwa alejki")
    opis = models.TextField(blank=True, verbose_name="Opis")
    kolejnosc = models.IntegerField(default=0, verbose_name="Kolejność na mapie")
    aktywna = models.BooleanField(default=True, verbose_name="Aktywna")
    orientacja = models.CharField(
        max_length=1, choices=Orientacja.choices, default=Orientacja.PIONOWA,
        verbose_name="Orientacja",
    )
    dlugosc = models.PositiveIntegerField(
        default=8, verbose_name="Długość (w kratkach)",
        help_text="Im większa wartość, tym dłuższa alejka na mapie.",
    )
    pozycja_x = models.IntegerField(default=0, verbose_name="Pozycja X (kratka)")
    pozycja_y = models.IntegerField(default=0, verbose_name="Pozycja Y (kratka)")

    class Meta:
        ordering = ['kolejnosc', 'nazwa']
        verbose_name = "Alejka"
        verbose_name_plural = "Alejki"

    def __str__(self):
        return self.nazwa


class ObiektMapy(models.Model):
    """Element mapy, ktory nie jest alejka: wykluczenie / strefa specjalna,
    np. stanowisko do projektowania mebli, kasa, magazyn, filar."""
    class Typ(models.TextChoices):
        WYKLUCZENIE = "WYKLUCZENIE", "Wykluczenie / strefa"
        STANOWISKO = "STANOWISKO", "Stanowisko"
        KASA = "KASA", "Kasa"
        MAGAZYN = "MAGAZYN", "Magazyn / zaplecze"
        INNE = "INNE", "Inne"

    nazwa = models.CharField(max_length=150, verbose_name="Nazwa")
    opis = models.TextField(blank=True, verbose_name="Opis")
    typ = models.CharField(max_length=20, choices=Typ.choices, default=Typ.WYKLUCZENIE, verbose_name="Typ")
    pozycja_x = models.IntegerField(default=0, verbose_name="Pozycja X (kratka)")
    pozycja_y = models.IntegerField(default=0, verbose_name="Pozycja Y (kratka)")
    szerokosc = models.PositiveIntegerField(default=3, verbose_name="Szerokość (w kratkach)")
    wysokosc = models.PositiveIntegerField(default=3, verbose_name="Wysokość (w kratkach)")
    aktywny = models.BooleanField(default=True, verbose_name="Aktywny")

    class Meta:
        ordering = ['nazwa']
        verbose_name = "Obiekt mapy"
        verbose_name_plural = "Obiekty mapy"

    def __str__(self):
        return f"{self.nazwa} ({self.get_typ_display()})"


class MiejsceProduktu(models.Model):
    """Produkt ustawiony w konkretnej alejce (strona + pozycja)."""
    class Strona(models.TextChoices):
        LEWA = "L", "Lewa"
        PRAWA = "P", "Prawa"

    alejka = models.ForeignKey(Alejka, on_delete=models.CASCADE, related_name='miejsca')
    # Produkt z katalogu ALBO wpis reczny (marka/model spoza moich marek).
    produkt = models.ForeignKey(
        Produkt, on_delete=models.CASCADE, related_name='miejsca', null=True, blank=True,
    )
    marka_tekst = models.CharField(max_length=100, blank=True, verbose_name="Marka (spoza katalogu)")
    model_tekst = models.CharField(max_length=150, blank=True, verbose_name="Model (spoza katalogu)")
    strona = models.CharField(max_length=1, choices=Strona.choices, default=Strona.LEWA)
    pozycja = models.PositiveIntegerField(default=0, verbose_name="Pozycja w alejce")

    class Meta:
        ordering = ['strona', 'pozycja']
        verbose_name = "Miejsce produktu"
        verbose_name_plural = "Miejsca produktów"

    @property
    def wyswietlana_marka(self):
        if self.produkt_id:
            return self.produkt.marka or ''
        return self.marka_tekst

    @property
    def wyswietlany_model(self):
        if self.produkt_id:
            return self.produkt.model
        return self.model_tekst

    def __str__(self):
        return f"{self.alejka.nazwa} [{self.get_strona_display()}#{self.pozycja}]: {self.wyswietlany_model}"


# Grupy marek uzywane do rozliczania targetow.
# Target "Beko" realizuja marki Beko + Grundig,
# target "Whirlpool" realizuja Whirlpool + Hotpoint + Indesit.
GRUPA_BEKO_MARKI = ('BEKO', 'GRUNDIG')
GRUPA_WHIRLPOOL_MARKI = ('WHIRLPOOL', 'HOTPOINT', 'INDESIT')


class Hala(models.Model):
    """Lokalizacja (hala/market) z przypisanymi pracownikami."""
    nazwa = models.CharField(max_length=150, verbose_name="Nazwa hali")
    opis = models.TextField(blank=True, verbose_name="Opis / lokalizacja")
    aktywna = models.BooleanField(default=True, verbose_name="Aktywna")
    pracownicy = models.ManyToManyField(
        User, related_name='hale', blank=True, verbose_name="Pracownicy",
    )

    class Meta:
        ordering = ['nazwa']
        verbose_name = "Hala"
        verbose_name_plural = "Hale"

    def __str__(self):
        return self.nazwa


class TargetHali(models.Model):
    """Target sprzedazowy hali. Rozliczenie jest kwartalne, ale cele moga byc
    zadane per miesiac (typowy przypadek) albo jednym numerem na caly kwartal."""
    class Typ(models.TextChoices):
        MIESIECZNY = "MIESIAC", "Miesięczny"
        KWARTALNY = "KWARTAL", "Kwartalny"

    hala = models.ForeignKey(Hala, on_delete=models.CASCADE, related_name='targety')
    typ = models.CharField(max_length=10, choices=Typ.choices, default=Typ.MIESIECZNY, verbose_name="Typ targetu")
    rok = models.PositiveIntegerField(verbose_name="Rok")
    kwartal = models.PositiveSmallIntegerField(
        choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')], verbose_name="Kwartał",
    )
    miesiac = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Miesiąc",
        help_text="Wypełniane tylko dla targetu miesięcznego.",
    )
    cel_beko = models.PositiveIntegerField(default=0, verbose_name="Cel Beko (szt.)")
    cel_whirlpool = models.PositiveIntegerField(default=0, verbose_name="Cel Whirlpool (szt.)")

    class Meta:
        ordering = ['-rok', '-kwartal', 'miesiac']
        verbose_name = "Target hali"
        verbose_name_plural = "Targety hal"
        constraints = [
            models.UniqueConstraint(
                fields=['hala', 'rok', 'miesiac'],
                condition=models.Q(miesiac__isnull=False),
                name='unikalny_target_miesieczny',
            ),
            models.UniqueConstraint(
                fields=['hala', 'rok', 'kwartal'],
                condition=models.Q(miesiac__isnull=True),
                name='unikalny_target_kwartalny',
            ),
        ]

    @staticmethod
    def kwartal_dla_miesiaca(miesiac):
        return (int(miesiac) - 1) // 3 + 1

    @staticmethod
    def miesiace_kwartalu(kwartal):
        start = (int(kwartal) - 1) * 3 + 1
        return [start, start + 1, start + 2]

    def save(self, *args, **kwargs):
        # Kwartal zawsze spojny z miesiacem; target kwartalny nie ma miesiaca.
        if self.typ == self.Typ.MIESIECZNY and self.miesiac:
            self.kwartal = self.kwartal_dla_miesiaca(self.miesiac)
        elif self.typ == self.Typ.KWARTALNY:
            self.miesiac = None
        super().save(*args, **kwargs)

    MIESIACE_PL = {
        1: 'Styczeń', 2: 'Luty', 3: 'Marzec', 4: 'Kwiecień', 5: 'Maj', 6: 'Czerwiec',
        7: 'Lipiec', 8: 'Sierpień', 9: 'Wrzesień', 10: 'Październik', 11: 'Listopad', 12: 'Grudzień',
    }

    @property
    def nazwa_okresu(self):
        if self.miesiac:
            return f"{self.MIESIACE_PL.get(self.miesiac, self.miesiac)} {self.rok}"
        return f"{self.rok} Q{self.kwartal}"

    def __str__(self):
        if self.miesiac:
            return f"{self.hala.nazwa} {self.rok}-{self.miesiac:02d}: B{self.cel_beko}/W{self.cel_whirlpool}"
        return f"{self.hala.nazwa} {self.rok} Q{self.kwartal}: B{self.cel_beko}/W{self.cel_whirlpool}"