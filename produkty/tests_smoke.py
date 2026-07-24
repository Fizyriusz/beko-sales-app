import io
from datetime import date, timedelta
from decimal import Decimal

import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Sprzedaz, Zadanie, DzienPracy, Alejka, MiejsceProduktu


def _xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["GRUPA TOWAROWA", "MARKA", "MODEL", "STAWKA"])
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return SimpleUploadedFile(
        "baza.xlsx", buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


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


class MapaMarketuTestCase(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="mapadm", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="mapadm", password="pass")
        self.p = Produkt.objects.create(model="LODOWKA1", stawka=Decimal("20"), grupa_towarowa="CHLODNICTWO", marka="BEKO")
        self.alejka = Alejka.objects.create(nazwa="Alejka Beko", opis="Lodowki", kolejnosc=1)

    def test_mapa_podglad(self):
        MiejsceProduktu.objects.create(alejka=self.alejka, produkt=self.p, strona="L", pozycja=1)
        r = self.client.get(reverse("produkty:mapa_marketu"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["ma_alejki"])
        self.assertEqual(r.context["alejki_json"][0]["lewa"][0]["model"], "LODOWKA1")
        self.assertTrue(r.context["alejki_json"][0]["lewa"][0]["is_beko"])

    def test_dodaj_alejke(self):
        r = self.client.post(reverse("produkty:mapa_zarzadzaj"), {"nazwa": "Nowa", "opis": "", "kolejnosc": 2, "aktywna": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Alejka.objects.filter(nazwa="Nowa").exists())

    def test_dodaj_i_usun_produkt(self):
        r = self.client.post(reverse("produkty:miejsce_dodaj", args=[self.alejka.id]), {"produkt": self.p.id, "strona": "P", "pozycja": 3})
        self.assertEqual(r.status_code, 302)
        m = MiejsceProduktu.objects.get(alejka=self.alejka, produkt=self.p)
        self.assertEqual(m.strona, "P")
        r2 = self.client.post(reverse("produkty:miejsce_usun", args=[m.id]))
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(MiejsceProduktu.objects.filter(id=m.id).exists())

    def test_edytuj_i_usun_alejke(self):
        r = self.client.get(reverse("produkty:alejka_edytuj", args=[self.alejka.id]))
        self.assertEqual(r.status_code, 200)
        r2 = self.client.post(reverse("produkty:alejka_usun", args=[self.alejka.id]))
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(Alejka.objects.filter(id=self.alejka.id).exists())


class ImportTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="imp", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="imp", password="pass")

    def test_import_normalizuje_i_stempluje_date(self):
        # istniejacy produkt (jak z auto-utworzenia przy sprzedazy) - WIELKIE litery, stawka 0
        Produkt.objects.create(model="WHSP70T262P", stawka=Decimal("0"), grupa_towarowa="NIEZNANA", marka="Nieznana")
        f = _xlsx([("COOLING NF", "whirlpool", "  whsp70t262p ", 60)])  # inny case + spacje
        r = self.client.post(reverse("produkty:import_excel"), {"file": f})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Produkt.objects.filter(model__iexact="WHSP70T262P").count(), 1)  # brak duplikatu
        p = Produkt.objects.get(model="WHSP70T262P")
        self.assertEqual(p.stawka, Decimal("60"))
        self.assertEqual(p.data_aktualizacji, date.today())
        self.assertEqual(r.context["liczba_zaktualizowanych"], 1)

    def test_import_tworzy_wielkimi_literami(self):
        f = _xlsx([("HOOD", "beko", "newmodel1", 45)])
        self.client.post(reverse("produkty:import_excel"), {"file": f})
        self.assertTrue(Produkt.objects.filter(model="NEWMODEL1").exists())

    def test_wyzerowanie_spoza_pliku(self):
        keep = Produkt.objects.create(model="INFILE", stawka=Decimal("50"), grupa_towarowa="X", marka="BEKO")
        gone = Produkt.objects.create(model="NOTINFILE", stawka=Decimal("50"), grupa_towarowa="X", marka="BEKO")
        f = _xlsx([("X", "BEKO", "INFILE", 55)])
        r = self.client.post(reverse("produkty:import_excel"), {"file": f, "wyzeruj_spoza": "on"})
        keep.refresh_from_db()
        gone.refresh_from_db()
        self.assertEqual(keep.stawka, Decimal("55"))
        self.assertEqual(gone.stawka, Decimal("0"))
        self.assertTrue(Produkt.objects.filter(model="NOTINFILE").exists())  # nie usuniety
        self.assertEqual(r.context["wyzerowane"], 1)

    def test_bez_wyzerowania_bez_flagi(self):
        gone = Produkt.objects.create(model="STAYS", stawka=Decimal("50"), grupa_towarowa="X", marka="BEKO")
        self.client.post(reverse("produkty:import_excel"), {"file": _xlsx([("X", "BEKO", "OTHER", 55)])})
        gone.refresh_from_db()
        self.assertEqual(gone.stawka, Decimal("50"))


class ProductDeleteTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="del", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="del", password="pass")

    def test_usun_produkt_ze_sprzedaza(self):
        p = Produkt.objects.create(model="DELME", stawka=Decimal("10"), grupa_towarowa="X", marka="BEKO")
        Sprzedaz.objects.create(produkt=p, liczba_sztuk=1, data_sprzedazy=date.today())
        r = self.client.get(reverse("produkty:product_delete", args=[p.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["liczba_sprzedazy"], 1)
        r2 = self.client.post(reverse("produkty:product_delete", args=[p.id]))
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(Produkt.objects.filter(id=p.id).exists())
        self.assertEqual(Sprzedaz.objects.filter(produkt_id=p.id).count(), 0)
