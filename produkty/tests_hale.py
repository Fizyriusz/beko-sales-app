from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Sprzedaz, Hala, TargetHali


class HaleTargetyTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="szef", password="pass", is_staff=True)
        self.prac = User.objects.create_user(username="prac1", password="pass")
        self.obcy = User.objects.create_user(username="obcy", password="pass")
        self.client = Client()
        self.client.login(username="szef", password="pass")

        self.hala = Hala.objects.create(nazwa="Hala Rzeszow")
        self.hala.pracownicy.add(self.prac)

        # Grupa Beko = BEKO + GRUNDIG; grupa Whirlpool = WHIRLPOOL + HOTPOINT + INDESIT
        self.p_beko = Produkt.objects.create(model="B1", stawka=Decimal("10"), grupa_towarowa="X", marka="BEKO")
        self.p_grundig = Produkt.objects.create(model="G1", stawka=Decimal("10"), grupa_towarowa="X", marka="Grundig")
        self.p_whirl = Produkt.objects.create(model="W1", stawka=Decimal("10"), grupa_towarowa="X", marka="WHIRLPOOL")
        self.p_hotpoint = Produkt.objects.create(model="H1", stawka=Decimal("10"), grupa_towarowa="X", marka="HOTPOINT")
        self.p_indesit = Produkt.objects.create(model="I1", stawka=Decimal("10"), grupa_towarowa="X", marka="INDESIT")
        self.p_obcy = Produkt.objects.create(model="S1", stawka=Decimal("10"), grupa_towarowa="X", marka="SAMSUNG")

    def _sprzedaz(self, produkt, dzien, ile=1, user=-1):
        Sprzedaz.objects.create(
            produkt=produkt, liczba_sztuk=ile, data_sprzedazy=dzien,
            user=self.prac if user == -1 else user,
        )

    def _realizacja(self, rok=2026, kwartal=3):
        url = reverse("produkty:realizacja_targetu_hali", args=[self.hala.id])
        return self.client.get(f"{url}?rok={rok}&kwartal={kwartal}")

    def test_grupy_marek_sumuja_sie_poprawnie(self):
        # Q3 2026 = lipiec, sierpien, wrzesien
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 3)
        self._sprzedaz(self.p_grundig, date(2026, 7, 6), 2)      # Beko: 3+2 = 5
        self._sprzedaz(self.p_whirl, date(2026, 7, 7), 1)
        self._sprzedaz(self.p_hotpoint, date(2026, 7, 8), 2)
        self._sprzedaz(self.p_indesit, date(2026, 7, 9), 4)      # Whirlpool: 1+2+4 = 7
        self._sprzedaz(self.p_obcy, date(2026, 7, 10), 99)       # obca marka - nie liczy sie

        TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=3, miesiac=7,
                                  cel_beko=130, cel_whirlpool=100)

        r = self._realizacja()
        self.assertEqual(r.status_code, 200)
        lipiec = r.context["postep"]["wiersze"][0]
        self.assertEqual(lipiec["nazwa"], "Lipiec")
        self.assertEqual(lipiec["real_beko"], 5)
        self.assertEqual(lipiec["real_whirlpool"], 7)
        self.assertEqual(lipiec["cel_beko"], 130)

    def test_rozliczenie_kwartalne_to_suma_celow_miesiecznych(self):
        for m in (7, 8, 9):
            TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=3, miesiac=m,
                                      cel_beko=130, cel_whirlpool=100)
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 100)
        self._sprzedaz(self.p_beko, date(2026, 8, 5), 100)
        self._sprzedaz(self.p_whirl, date(2026, 9, 5), 50)

        suma = self._realizacja().context["postep"]["suma"]
        self.assertEqual(suma["cel_beko"], 390)        # 3 x 130
        self.assertEqual(suma["cel_whirlpool"], 300)   # 3 x 100
        self.assertEqual(suma["real_beko"], 200)
        self.assertEqual(suma["real_whirlpool"], 50)
        self.assertEqual(suma["brakuje_beko"], 190)

    def test_target_kwartalny_nadpisuje_rozliczenie(self):
        TargetHali.objects.create(hala=self.hala, typ="KWARTAL", rok=2026, kwartal=3,
                                  cel_beko=300, cel_whirlpool=250)
        self._sprzedaz(self.p_beko, date(2026, 8, 5), 150)

        suma = self._realizacja().context["postep"]["suma"]
        self.assertEqual(suma["cel_beko"], 300)
        self.assertEqual(suma["real_beko"], 150)
        self.assertEqual(suma["proc_beko"], 50.0)
        self.assertIsNone(TargetHali.objects.get(typ="KWARTAL").miesiac)

    def test_liczy_tylko_pracownikow_hali(self):
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 10)                  # pracownik hali
        self._sprzedaz(self.p_beko, date(2026, 7, 6), 7, user=self.obcy)   # ktos z innej hali
        self._sprzedaz(self.p_beko, date(2026, 7, 7), 5, user=None)        # bez konta
        TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=3, miesiac=7, cel_beko=100)

        r = self._realizacja()
        self.assertEqual(r.context["postep"]["wiersze"][0]["real_beko"], 10)

    def test_sprzedaz_poza_kwartalem_nie_liczy(self):
        self._sprzedaz(self.p_beko, date(2026, 6, 30), 50)   # Q2
        self._sprzedaz(self.p_beko, date(2026, 10, 1), 50)   # Q4
        TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=3, miesiac=7, cel_beko=100)

        self.assertEqual(self._realizacja().context["postep"]["suma"]["real_beko"], 0)

    def test_kwartal_wyliczany_z_miesiaca(self):
        t = TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=1, miesiac=11, cel_beko=10)
        self.assertEqual(t.kwartal, 4)  # listopad -> Q4

    def test_dodanie_hali_z_pracownikiem(self):
        r = self.client.post(reverse("produkty:hale_lista"), {
            "nazwa": "Hala Krakow", "opis": "", "pracownicy": [self.prac.id], "aktywna": "on",
        })
        self.assertEqual(r.status_code, 302)
        h = Hala.objects.get(nazwa="Hala Krakow")
        self.assertIn(self.prac, h.pracownicy.all())

    def test_dodanie_targetu_przez_formularz(self):
        r = self.client.post(reverse("produkty:hala_edytuj", args=[self.hala.id]), {
            "typ_formularza": "target", "typ": "MIESIAC", "rok": 2026, "kwartal": 3,
            "miesiac": 8, "cel_beko": 130, "cel_whirlpool": 100,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(TargetHali.objects.get(hala=self.hala, miesiac=8).cel_beko, 130)

    def test_target_miesieczny_wymaga_miesiaca(self):
        r = self.client.post(reverse("produkty:hala_edytuj", args=[self.hala.id]), {
            "typ_formularza": "target", "typ": "MIESIAC", "rok": 2026, "kwartal": 3,
            "miesiac": "", "cel_beko": 130, "cel_whirlpool": 100,
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(TargetHali.objects.count(), 0)

    def test_pracownik_widzi_tylko_swoja_hale(self):
        obca_hala = Hala.objects.create(nazwa="Obca")
        c = Client()
        c.login(username="prac1", password="pass")
        r = c.get(reverse("produkty:realizacja_targetu"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["hala"], self.hala)
        r2 = c.get(reverse("produkty:realizacja_targetu_hali", args=[obca_hala.id]))
        self.assertEqual(r2.status_code, 404)

    def test_podsumowanie_dzieli_na_grupy(self):
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 3)
        self._sprzedaz(self.p_grundig, date(2026, 7, 5), 2)
        self._sprzedaz(self.p_whirl, date(2026, 7, 5), 4)
        self._sprzedaz(self.p_obcy, date(2026, 7, 5), 1)

        r = self.client.get(reverse("produkty:podsumowanie_sprzedazy") + "?data_od=2026-07-01&data_do=2026-07-31")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["suma_beko"]["sztuki"], 5)
        self.assertEqual(r.context["suma_whirlpool"]["sztuki"], 4)
        self.assertEqual(r.context["suma_inne"]["sztuki"], 1)

    def test_przypisanie_historycznej_sprzedazy(self):
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 5, user=None)
        self._sprzedaz(self.p_beko, date(2026, 7, 6), 5, user=None)

        r = self.client.get(reverse("produkty:przypisz_sprzedaze"))
        self.assertEqual(r.context["liczba_bez_uzytkownika"], 2)
        r2 = self.client.post(reverse("produkty:przypisz_sprzedaze"), {"user": self.prac.id})
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(Sprzedaz.objects.filter(user__isnull=True).count(), 0)
        self.assertEqual(Sprzedaz.objects.filter(user=self.prac).count(), 2)

    def test_nowa_sprzedaz_zapisuje_konto(self):
        c = Client()
        c.login(username="prac1", password="pass")
        c.post(reverse("produkty:sprzedaz"), {"data_sprzedazy": "2026-07-15", "modele_sprzedazy": "B1"})
        s = Sprzedaz.objects.filter(produkt=self.p_beko).first()
        self.assertIsNotNone(s)
        self.assertEqual(s.user, self.prac)

    def test_usuniecie_hali_nie_rusza_sprzedazy(self):
        self._sprzedaz(self.p_beko, date(2026, 7, 5), 4)
        TargetHali.objects.create(hala=self.hala, typ="MIESIAC", rok=2026, kwartal=3, miesiac=7, cel_beko=100)
        r = self.client.post(reverse("produkty:hala_usun", args=[self.hala.id]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Hala.objects.filter(id=self.hala.id).exists())
        self.assertEqual(TargetHali.objects.count(), 0)
        self.assertEqual(Sprzedaz.objects.count(), 1)          # sprzedaz zostaje
        self.assertTrue(User.objects.filter(id=self.prac.id).exists())  # konto zostaje
