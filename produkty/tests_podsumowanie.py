from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Produkt, Sprzedaz, Zadanie


class PodsumowanieZadaniaKasaTestCase(TestCase):
    """Rozliczenie zadan w podsumowaniu sprzedazy: widocznosc wszystkich zadan
    oraz rozbicie zarobku na sprzedaz / zadania / sume."""

    OKRES = "?data_od=2026-07-01&data_do=2026-07-31"

    def setUp(self):
        self.user = User.objects.create_user(username="sprzedawca", password="pass")
        self.client = Client()
        self.client.login(username="sprzedawca", password="pass")

        self.p = Produkt.objects.create(model="PRALKA1", stawka=Decimal("10"), grupa_towarowa="PRALKI", marka="BEKO")
        # baza = 3*10 + 2*10 = 50; bonus mnoznikowy zapisany przy sprzedazy = 15
        Sprzedaz.objects.create(produkt=self.p, liczba_sztuk=3, data_sprzedazy=date(2026, 7, 10))
        Sprzedaz.objects.create(produkt=self.p, liczba_sztuk=2, data_sprzedazy=date(2026, 7, 11),
                                prowizja=Decimal("15"))

    def _zadanie(self, nazwa, **kwargs):
        z = Zadanie.objects.create(
            nazwa=nazwa,
            data_start=date(2026, 7, 1),
            data_koniec=date(2026, 7, 31),
            **kwargs,
        )
        z.produkty.add(self.p)
        return z

    def _podsumowanie(self):
        return self.client.get(reverse("produkty:podsumowanie_sprzedazy") + self.OKRES)

    def test_zadanie_mix_mnoznik_jest_widoczne(self):
        """Wczesniej zadania typu Mix mnoznik nigdy sie nie pokazywaly,
        bo nie maja premii progowej."""
        self._zadanie("Mnoznik pralki", typ=Zadanie.Typ.MIX_MNOZNIK,
                      prog_mix=4, mnoznik_mix=Decimal("1.5"))
        r = self._podsumowanie()
        self.assertEqual(r.status_code, 200)
        nazwy = [t["nazwa"] for t in r.context["task_rewards"]]
        self.assertIn("Mnoznik pralki", nazwy)
        wpis = r.context["task_rewards"][0]
        self.assertTrue(wpis["wykonane"])
        self.assertEqual(wpis["bonus_mnoznik"], Decimal("15"))

    def test_wszystkie_wykonane_zadania_sa_widoczne(self):
        """Sedno zgloszenia: pokazywalo sie tylko jedno zadanie."""
        self._zadanie("Progowe z premia", prog_1=5, prog_1_premia=Decimal("100"))
        self._zadanie("Mnoznikowe", typ=Zadanie.Typ.MIX_MNOZNIK, prog_mix=4, mnoznik_mix=Decimal("1.5"))
        self._zadanie("Progowe bez kwoty", prog_1=5)  # wykonane, ale premia nieustawiona

        r = self._podsumowanie()
        wykonane = [t["nazwa"] for t in r.context["task_rewards"] if t["wykonane"]]
        self.assertEqual(len(wykonane), 3)
        self.assertIn("Progowe z premia", wykonane)
        self.assertIn("Mnoznikowe", wykonane)
        self.assertIn("Progowe bez kwoty", wykonane)

    def test_zadanie_niewykonane_tez_widoczne_ale_oznaczone(self):
        self._zadanie("Daleko do celu", prog_1=999, prog_1_premia=Decimal("500"))
        r = self._podsumowanie()
        wpis = [t for t in r.context["task_rewards"] if t["nazwa"] == "Daleko do celu"][0]
        self.assertFalse(wpis["wykonane"])
        self.assertEqual(wpis["premia"], Decimal("0.00"))
        self.assertEqual(wpis["sprzedane"], 5)

    def test_wykonane_sortowane_na_gore(self):
        self._zadanie("Niewykonane", prog_1=999, prog_1_premia=Decimal("500"))
        self._zadanie("Wykonane", prog_1=5, prog_1_premia=Decimal("100"))
        r = self._podsumowanie()
        self.assertEqual(r.context["task_rewards"][0]["nazwa"], "Wykonane")

    def test_rozbicie_kwoty_sprzedaz_zadania_suma(self):
        self._zadanie("Progowe", prog_1=5, prog_1_premia=Decimal("100"))
        self._zadanie("Mnoznikowe", typ=Zadanie.Typ.MIX_MNOZNIK, prog_mix=4, mnoznik_mix=Decimal("1.5"))

        r = self._podsumowanie()
        ctx = r.context
        self.assertEqual(ctx["prowizja_ze_sprzedazy"], Decimal("50"))    # 3*10 + 2*10
        self.assertEqual(ctx["bonus_mnoznikowy"], Decimal("15"))         # pole prowizja przy sprzedazy
        self.assertEqual(ctx["premie_progowe"], Decimal("100"))
        self.assertEqual(ctx["prowizja_z_zadan"], Decimal("115"))        # 15 + 100
        self.assertEqual(ctx["suma_calkowita"], Decimal("165"))          # 50 + 115

    def test_brak_podwojnego_liczenia_bonusu(self):
        """Dwa zadania mnoznikowe na tych samych produktach nie moga zdublowac
        bonusu w sumie calkowitej."""
        self._zadanie("Mnoznik A", typ=Zadanie.Typ.MIX_MNOZNIK, prog_mix=4, mnoznik_mix=Decimal("1.5"))
        self._zadanie("Mnoznik B", typ=Zadanie.Typ.MIX_MNOZNIK, prog_mix=4, mnoznik_mix=Decimal("2"))

        ctx = self._podsumowanie().context
        self.assertEqual(ctx["bonus_mnoznikowy"], Decimal("15"))   # nie 30
        self.assertEqual(ctx["suma_calkowita"], Decimal("65"))     # 50 + 15

    def test_suma_zgadza_sie_z_czesciami(self):
        self._zadanie("Progowe", prog_1=5, prog_1_premia=Decimal("100"))
        ctx = self._podsumowanie().context
        self.assertEqual(
            ctx["suma_calkowita"],
            ctx["prowizja_ze_sprzedazy"] + ctx["prowizja_z_zadan"],
        )
        self.assertEqual(
            ctx["prowizja_z_zadan"],
            ctx["bonus_mnoznikowy"] + ctx["premie_progowe"],
        )

    def test_zadanie_spoza_okresu_nie_liczy_sie(self):
        z = Zadanie.objects.create(nazwa="Sierpniowe", data_start=date(2026, 8, 1), data_koniec=date(2026, 8, 31),
                                   prog_1=1, prog_1_premia=Decimal("999"))
        z.produkty.add(self.p)
        ctx = self._podsumowanie().context
        self.assertEqual([t["nazwa"] for t in ctx["task_rewards"]], [])
        self.assertEqual(ctx["premie_progowe"], Decimal("0.00"))

    def test_wyzszy_prog_ma_pierwszenstwo(self):
        self._zadanie("Dwa progi", prog_1=3, prog_1_premia=Decimal("50"),
                      prog_2=5, prog_2_premia=Decimal("120"))
        ctx = self._podsumowanie().context
        wpis = ctx["task_rewards"][0]
        self.assertEqual(wpis["premia"], Decimal("120"))
        self.assertEqual(wpis["prog_osiagniety"], 5)
