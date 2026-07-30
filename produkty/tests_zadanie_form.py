from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Zadanie


class ZadanieEdycjaPremiiTestCase(TestCase):
    """Formularz zadania musi pozwalac ustawic premie i nie moze kasowac
    juz zapisanych wartosci przy edycji."""

    def setUp(self):
        self.user = User.objects.create_user(username="edytor", password="pass")
        self.client = Client()
        self.client.login(username="edytor", password="pass")
        self.p = Produkt.objects.create(model="PRALKA1", stawka=Decimal("10"), grupa_towarowa="PRALKI", marka="BEKO")

    def _zadanie(self, **kwargs):
        dane = dict(
            nazwa="Zadanie", data_start=date(2026, 7, 1), data_koniec=date(2026, 7, 31),
            typ=Zadanie.Typ.KONKRETNE_MODELE, prog_1=5, prog_1_premia=Decimal("300"),
        )
        dane.update(kwargs)
        z = Zadanie.objects.create(**dane)
        z.produkty.add(self.p)
        return z

    def test_formularz_zawiera_pola_premii(self):
        z = self._zadanie()
        r = self.client.get(reverse("produkty:edytuj_zadanie", args=[z.id]))
        self.assertEqual(r.status_code, 200)
        for pole in ("prog_1_premia", "prog_2_premia", "prog_mix", "mnoznik_mix", "typ"):
            self.assertContains(r, f'name="{pole}"', msg_prefix=f"Brak pola {pole} w formularzu")

    def test_edycja_nie_kasuje_premii(self):
        """Regresja: brak pol premii w szablonie powodowal ich wyzerowanie."""
        z = self._zadanie(prog_2=8, prog_2_premia=Decimal("500"))
        r = self.client.post(reverse("produkty:edytuj_zadanie", args=[z.id]), {
            "nazwa": "Zadanie po edycji",
            "opis": "",
            "data_start": "2026-07-01",
            "data_koniec": "2026-07-31",
            "typ": Zadanie.Typ.KONKRETNE_MODELE,
            "target": "ilosc",
            "prog_1": 5,
            "prog_1_premia": "300",
            "prog_2": 8,
            "prog_2_premia": "500",
            "produkty": [self.p.id],
        })
        self.assertEqual(r.status_code, 302)
        z.refresh_from_db()
        self.assertEqual(z.nazwa, "Zadanie po edycji")
        self.assertEqual(z.prog_1_premia, Decimal("300"))
        self.assertEqual(z.prog_2_premia, Decimal("500"))
        self.assertEqual(z.typ, Zadanie.Typ.KONKRETNE_MODELE)

    def test_mozna_ustawic_premie_przez_formularz(self):
        z = self._zadanie(prog_1_premia=None)
        self.assertIsNone(z.prog_1_premia)
        r = self.client.post(reverse("produkty:edytuj_zadanie", args=[z.id]), {
            "nazwa": "Zadanie",
            "opis": "",
            "data_start": "2026-07-01",
            "data_koniec": "2026-07-31",
            "typ": Zadanie.Typ.KONKRETNE_MODELE,
            "target": "ilosc",
            "prog_1": 5,
            "prog_1_premia": "250.50",
            "produkty": [self.p.id],
        })
        self.assertEqual(r.status_code, 302)
        z.refresh_from_db()
        self.assertEqual(z.prog_1_premia, Decimal("250.50"))

    def test_edycja_zadania_mnoznikowego_zachowuje_mnoznik(self):
        z = self._zadanie(typ=Zadanie.Typ.MIX_MNOZNIK, prog_1=None, prog_1_premia=None,
                          prog_mix=4, mnoznik_mix=Decimal("1.5"))
        r = self.client.post(reverse("produkty:edytuj_zadanie", args=[z.id]), {
            "nazwa": "Mnoznikowe",
            "opis": "",
            "data_start": "2026-07-01",
            "data_koniec": "2026-07-31",
            "typ": Zadanie.Typ.MIX_MNOZNIK,
            "target": "ilosc",
            "prog_mix": 4,
            "mnoznik_mix": "2.0",
            "produkty": [self.p.id],
        })
        self.assertEqual(r.status_code, 302)
        z.refresh_from_db()
        self.assertEqual(z.mnoznik_mix, Decimal("2.0"))
        self.assertEqual(z.prog_mix, 4)
        self.assertEqual(z.typ, Zadanie.Typ.MIX_MNOZNIK)

    def test_stare_zadanie_bez_typu_dostaje_domyslny(self):
        """Zadania zapisane wczesniej moga miec pusty typ - formularz ma
        podstawic sensowna wartosc zamiast wysypywac walidacje."""
        z = self._zadanie()
        Zadanie.objects.filter(id=z.id).update(typ="")
        r = self.client.get(reverse("produkty:edytuj_zadanie", args=[z.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["form"]["typ"].value(), Zadanie.Typ.KONKRETNE_MODELE)
