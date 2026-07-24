from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Sprzedaz, Zadanie, DzienPracy


class SmokeRenderTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="smoke", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="smoke", password="pass")
        self.today = date.today()

        self.p1 = Produkt.objects.create(model="B3RCNA404HXBR", stawka=Decimal("15"), grupa_towarowa="CHLODNICTWO", marka="BEKO")
        self.p2 = Produkt.objects.create(model="B3RCNA364HXBR", stawka=Decimal("10"), grupa_towarowa="", marka="")
        # sprzedaz p1 w tym miesiacu (do postepu i kalendarza)
        Sprzedaz.objects.create(produkt=self.p1, liczba_sztuk=2, data_sprzedazy=self.today)
        # sprzedaz p1 spoza okresu zadania (200 dni temu) - do wskazowki diagnostycznej
        Sprzedaz.objects.create(produkt=self.p1, liczba_sztuk=1, data_sprzedazy=self.today - timedelta(days=200))

        DzienPracy.objects.create(user=self.user, data=self.today)

        self.zad = Zadanie.objects.create(
            nazwa="Chlodnictwo", data_start=self.today, data_koniec=self.today, prog_1=8, prog_2=12,
        )
        self.zad.produkty.set([self.p1, self.p2])

    def test_lista_produktow(self):
        r = self.client.get(reverse("produkty:lista_produktow"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("dostepne_grupy", r.context)
        self.assertIn("dostepne_marki", r.context)

    def test_lista_produktow_grouped(self):
        r = self.client.get(reverse("produkty:lista_produktow") + "?group=grupa_towarowa")
        self.assertEqual(r.status_code, 200)

    def test_grupy_marki(self):
        r = self.client.get(reverse("produkty:grupy_marki"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "CHLODNICTWO")

    def test_calendar(self):
        r = self.client.get(reverse("produkty:calendar", args=[self.today.year, self.today.month]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("work_days", r.context)
        self.assertIn(self.today.day, r.context["work_days"])

    def test_szczegoly_zadania(self):
        r = self.client.get(reverse("produkty:szczegoly_zadania", args=[self.zad.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["postep"], 2)
        self.assertTrue(r.context["ma_sprzedaz_historyczna"])


class ZamianaMarkaGrupaTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="adm", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="adm", password="pass")
        # zle zaimportowany produkt: marka i grupa zamienione miejscami
        self.p = Produkt.objects.create(model="ZLE1", stawka=Decimal("10"), grupa_towarowa="BEKO", marka="COOLING")
        # poprawny produkt - nie powinien zostac ruszony
        self.ok = Produkt.objects.create(model="OK1", stawka=Decimal("10"), grupa_towarowa="AGD", marka="WHIRLPOOL")

    def test_get_renders(self):
        r = self.client.get(reverse("produkty:zamiana_marka_grupa"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("pokaz_podglad", r.context)

    def test_preview_does_not_mutate(self):
        r = self.client.post(reverse("produkty:zamiana_marka_grupa"), {"akcja": "podglad", "grupa": ["BEKO"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["liczba_podglad"], 1)
        self.p.refresh_from_db()
        self.assertEqual(self.p.marka, "COOLING")  # bez zmian
        self.assertEqual(self.p.grupa_towarowa, "BEKO")

    def test_swap_applies(self):
        r = self.client.post(reverse("produkty:zamiana_marka_grupa"), {"akcja": "zamien", "grupa": ["BEKO"]})
        self.assertEqual(r.status_code, 302)
        self.p.refresh_from_db()
        self.assertEqual(self.p.marka, "BEKO")
        self.assertEqual(self.p.grupa_towarowa, "COOLING")
        # niezaznaczony produkt bez zmian
        self.ok.refresh_from_db()
        self.assertEqual(self.ok.marka, "WHIRLPOOL")
        self.assertEqual(self.ok.grupa_towarowa, "AGD")
