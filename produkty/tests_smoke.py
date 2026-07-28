import io
from datetime import date, timedelta
from decimal import Decimal

import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Sprzedaz, Zadanie, DzienPracy, Alejka, MiejsceProduktu, ObiektMapy


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
        wpis = r.context["alejki_json"][0]["lewa"][0]
        self.assertEqual(wpis["model"], "LODOWKA1")
        self.assertTrue(wpis["moja_marka"])
        self.assertTrue(wpis["z_katalogu"])
        # dane ukladu alejki trafiaja do renderera
        self.assertIn("orientacja", r.context["alejki_json"][0])
        self.assertIn("dlugosc", r.context["alejki_json"][0])

    def test_cztery_moje_marki(self):
        for marka in ["WHIRLPOOL", "GRUNDIG", "INDESIT"]:
            p = Produkt.objects.create(model=f"M-{marka}", stawka=Decimal("10"), grupa_towarowa="X", marka=marka)
            MiejsceProduktu.objects.create(alejka=self.alejka, produkt=p, strona="L", pozycja=1)
        obca = Produkt.objects.create(model="M-SAMSUNG", stawka=Decimal("10"), grupa_towarowa="X", marka="SAMSUNG")
        MiejsceProduktu.objects.create(alejka=self.alejka, produkt=obca, strona="L", pozycja=9)
        r = self.client.get(reverse("produkty:mapa_marketu"))
        wpisy = {w["model"]: w["moja_marka"] for w in r.context["alejki_json"][0]["lewa"]}
        self.assertTrue(wpisy["M-WHIRLPOOL"])
        self.assertTrue(wpisy["M-GRUNDIG"])
        self.assertTrue(wpisy["M-INDESIT"])
        self.assertFalse(wpisy["M-SAMSUNG"])

    def test_dodaj_alejke(self):
        r = self.client.post(reverse("produkty:mapa_zarzadzaj"), {
            "typ_formularza": "alejka", "nazwa": "Nowa", "opis": "", "kolejnosc": 2,
            "orientacja": "H", "dlugosc": 12, "pozycja_x": 3, "pozycja_y": 5, "aktywna": "on",
        })
        self.assertEqual(r.status_code, 302)
        a = Alejka.objects.get(nazwa="Nowa")
        self.assertEqual(a.orientacja, "H")
        self.assertEqual(a.dlugosc, 12)
        self.assertEqual((a.pozycja_x, a.pozycja_y), (3, 5))

    def test_obiekt_wykluczenia(self):
        r = self.client.post(reverse("produkty:mapa_zarzadzaj"), {
            "typ_formularza": "obiekt", "nazwa": "Stanowisko projektowania mebli",
            "typ": "STANOWISKO", "opis": "", "pozycja_x": 2, "pozycja_y": 2,
            "szerokosc": 4, "wysokosc": 3, "aktywny": "on",
        })
        self.assertEqual(r.status_code, 302)
        o = ObiektMapy.objects.get(nazwa="Stanowisko projektowania mebli")
        self.assertEqual(o.szerokosc, 4)
        # obiekt trafia na mape
        r2 = self.client.get(reverse("produkty:mapa_marketu"))
        self.assertEqual(r2.context["obiekty_json"][0]["nazwa"], "Stanowisko projektowania mebli")
        # i da sie go usunac
        r3 = self.client.post(reverse("produkty:obiekt_usun", args=[o.id]))
        self.assertEqual(r3.status_code, 302)
        self.assertFalse(ObiektMapy.objects.filter(id=o.id).exists())

    def test_produkt_spoza_katalogu(self):
        r = self.client.post(reverse("produkty:miejsce_dodaj", args=[self.alejka.id]), {
            "marka_tekst": "samsung", "model_tekst": "RB34T672FSA", "strona": "P", "pozycja": 2,
        })
        self.assertEqual(r.status_code, 302)
        m = MiejsceProduktu.objects.get(model_tekst="RB34T672FSA")
        self.assertIsNone(m.produkt_id)
        self.assertEqual(m.wyswietlany_model, "RB34T672FSA")
        r2 = self.client.get(reverse("produkty:mapa_marketu"))
        wpis = r2.context["alejki_json"][0]["prawa"][0]
        self.assertFalse(wpis["z_katalogu"])
        self.assertFalse(wpis["moja_marka"])

    def test_miejsce_bez_danych_odrzucone(self):
        r = self.client.post(reverse("produkty:miejsce_dodaj", args=[self.alejka.id]), {"strona": "L", "pozycja": 0})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(MiejsceProduktu.objects.filter(alejka=self.alejka).count(), 0)

    def test_widok_druku(self):
        MiejsceProduktu.objects.create(alejka=self.alejka, produkt=self.p, strona="L", pozycja=1)
        r = self.client.get(reverse("produkty:mapa_druk"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "LODOWKA1")
        self.assertContains(r, "Zapisz jako PDF")

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


class HistoriaProwizjaTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="hist", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="hist", password="pass")

    def test_prowizja_liczona_ze_stawki(self):
        p = Produkt.objects.create(model="P60", stawka=Decimal("60"), grupa_towarowa="X", marka="WHIRLPOOL")
        Sprzedaz.objects.create(produkt=p, liczba_sztuk=1, data_sprzedazy=date.today())  # prowizja=0
        Sprzedaz.objects.create(produkt=p, liczba_sztuk=1, data_sprzedazy=date.today(), prowizja=Decimal("20"))
        r = self.client.get(reverse("produkty:historia_sprzedazy_produktu", args=[p.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["suma_prowizji"], Decimal("140"))  # 60 + (60+20)
        za_sztuke = sorted(s.prowizja_za_sztuke for s in r.context["sprzedaz_list"])
        self.assertEqual(za_sztuke, [Decimal("60"), Decimal("80")])


class PolaczProduktyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mrg", password="pass", is_staff=True)
        self.client = Client()
        self.client.login(username="mrg", password="pass")
        self.src = Produkt.objects.create(model="WH8IA15AM3TUS0X", stawka=Decimal("0"), grupa_towarowa="X", marka="WHIRLPOOL")
        self.tgt = Produkt.objects.create(model="WH8IA15AM3TUS0", stawka=Decimal("60"), grupa_towarowa="X", marka="WHIRLPOOL")
        Sprzedaz.objects.create(produkt=self.src, liczba_sztuk=1, data_sprzedazy=date.today())
        Sprzedaz.objects.create(produkt=self.src, liczba_sztuk=1, data_sprzedazy=date.today())

    def test_podglad_nie_laczy(self):
        r = self.client.post(reverse("produkty:polacz_produkty"), {"akcja": "podglad", "source": self.src.id, "target": self.tgt.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["source_sprzedaz"], 2)
        self.assertTrue(Produkt.objects.filter(id=self.src.id).exists())

    def test_polaczenie_przenosi_sprzedaz(self):
        r = self.client.post(reverse("produkty:polacz_produkty"), {"akcja": "polacz", "source": self.src.id, "target": self.tgt.id})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Produkt.objects.filter(id=self.src.id).exists())
        self.assertEqual(Sprzedaz.objects.filter(produkt=self.tgt).count(), 2)

    def test_ten_sam_produkt_odrzucony(self):
        r = self.client.post(reverse("produkty:polacz_produkty"), {"akcja": "polacz", "source": self.src.id, "target": self.src.id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Produkt.objects.filter(id=self.src.id).exists())
