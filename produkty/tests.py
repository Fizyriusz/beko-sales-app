from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from .models import Produkt, Sprzedaz, Task


@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class SprzedazSugestieTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client = Client()
        self.client.login(username="tester", password="pass")

    def test_suggestion_flow_creates_sale(self):
        Produkt.objects.create(model="ABC123", stawka=10, grupa_towarowa="AGD")
        data_sprzedazy = "2024-01-01"

        response = self.client.post(
            reverse("produkty:sprzedaz"),
            {
                "data_sprzedazy": data_sprzedazy,
                "modele_sprzedazy": "ABC124",
            },
        )

        self.assertTemplateUsed(response, "produkty/sprzedaz_sugestie.html")

        response = self.client.post(
            reverse("produkty:sprzedaz"),
            {
                "sugestie_zatwierdzone": "1",
                "data_sprzedazy": data_sprzedazy,
                "model_1": "ABC123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Sprzedaz.objects.filter(produkt__model="ABC123").count(),
            1,
        )

        summary = self.client.get(reverse("produkty:podsumowanie_sprzedazy"))
        models_in_summary = [d["model"] for d in summary.context["sprzedaz"].values()]
        self.assertIn("ABC123", models_in_summary)

    def test_unique_models_no_duplicates(self):
        Produkt.objects.create(model="ABC123", stawka=10, grupa_towarowa="AGD")
        Produkt.objects.create(model="XYZ789", stawka=5, grupa_towarowa="AGD")

        data_sprzedazy = "2024-01-01"

        response = self.client.post(
            reverse("produkty:sprzedaz"),
            {
                "data_sprzedazy": data_sprzedazy,
                "modele_sprzedazy": "ABC123\nXYZ788\nNEWMODEL",
            },
        )

        self.assertTemplateUsed(response, "produkty/sprzedaz_sugestie.html")

        response = self.client.post(
            reverse("produkty:sprzedaz"),
            {
                "sugestie_zatwierdzone": "1",
                "data_sprzedazy": data_sprzedazy,
                "model_1": "ABC123",
                "model_2": "NEWMODEL",
                "model_3": "XYZ789",
            },
        )

        self.assertEqual(response.status_code, 302)

        unique_models = {"ABC123", "NEWMODEL", "XYZ789"}
        self.assertEqual(Sprzedaz.objects.count(), len(unique_models))

        summary = self.client.get(reverse("produkty:podsumowanie_sprzedazy"))
        models_in_summary = [d["model"] for d in summary.context["sprzedaz"].values()]

        self.assertEqual(len(models_in_summary), len(unique_models))
        self.assertEqual(len(set(models_in_summary)), len(unique_models))


@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class PodsumowanieZadaniowkiTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester2", password="pass")
        self.client = Client()
        self.client.login(username="tester2", password="pass")
        self.today = timezone.now().date()

    def test_mix_model_commission_task(self):
        p1 = Produkt.objects.create(model="M1", stawka=Decimal("10"), grupa_towarowa="AGD")
        p2 = Produkt.objects.create(model="M2", stawka=Decimal("10"), grupa_towarowa="AGD")
        task = Task.objects.create(
            nazwa="T1",
            minimalna_liczba_sztuk=5,
            premia_za_minimalna_liczbe=Decimal("100"),
            premia_za_dodatkowa_liczbe=Decimal("10"),
            mnoznik_stawki=1,
            data_od=self.today,
            data_do=self.today,
        )
        task.produkty.set([p1, p2])
        Sprzedaz.objects.create(produkt=p1, liczba_sztuk=3, data_sprzedazy=self.today)
        Sprzedaz.objects.create(produkt=p2, liczba_sztuk=4, data_sprzedazy=self.today)

        response = self.client.get(
            reverse("produkty:podsumowanie_sprzedazy") + "?task_type=commission"
        )
        self.assertEqual(response.context["task_rewards"][0]["premia"], Decimal("120"))

    def test_mix_model_multiplier_task(self):
        p = Produkt.objects.create(model="X1", stawka=Decimal("10"), grupa_towarowa="AGD")
        task = Task.objects.create(
            nazwa="Mult",
            minimalna_liczba_sztuk=0,
            mnoznik_stawki=Decimal("2"),
            data_od=self.today,
            data_do=self.today,
        )
        task.produkty.add(p)
        Sprzedaz.objects.create(produkt=p, liczba_sztuk=2, data_sprzedazy=self.today)

        response = self.client.get(
            reverse("produkty:podsumowanie_sprzedazy") + "?task_type=multiplier"
        )
        entry = list(response.context["sprzedaz"].values())[0]
        self.assertEqual(entry["stawka"], Decimal("20"))
        self.assertEqual(entry["suma_prowizji"], Decimal("40"))

    def test_specific_models_task(self):
        p = Produkt.objects.create(model="S1", stawka=Decimal("10"), grupa_towarowa="AGD")
        task = Task.objects.create(
            nazwa="Spec",
            minimalna_liczba_sztuk=0,
            premia_za_dodatkowa_liczbe=Decimal("5"),
            data_od=self.today,
            data_do=self.today,
        )
        task.produkty.add(p)
        Sprzedaz.objects.create(produkt=p, liczba_sztuk=3, data_sprzedazy=self.today)

        response = self.client.get(
            reverse("produkty:podsumowanie_sprzedazy") + "?task_type=specific"
        )
        entry = list(response.context["sprzedaz"].values())[0]
        self.assertEqual(entry["stawka"], Decimal("15"))
        self.assertEqual(entry["suma_prowizji"], Decimal("45"))

    def test_mix_prowizja_task_threshold(self):
        p1 = Produkt.objects.create(model="MP1", stawka=Decimal("10"), grupa_towarowa="AGD", marka="B")
        p2 = Produkt.objects.create(model="MP2", stawka=Decimal("10"), grupa_towarowa="AGD", marka="B")
        task = Task.objects.create(
            nazwa="MixProv",
            typ=Task.Typ.MIX_PROWIZJA,
            prog_mix=5,
            premia_za_minimalna_liczbe=Decimal("100"),
            premia_za_dodatkowa_liczbe=Decimal("20"),
            data_od=self.today,
            data_do=self.today,
        )
        task.produkty.set([p1, p2])
        Sprzedaz.objects.create(produkt=p1, liczba_sztuk=3, data_sprzedazy=self.today)
        Sprzedaz.objects.create(produkt=p2, liczba_sztuk=4, data_sprzedazy=self.today)

        response = self.client.get(reverse("produkty:podsumowanie_sprzedazy"))
        self.assertEqual(response.context["task_rewards"][0]["premia"], Decimal("140"))

    def test_mix_mnoznik_task_threshold(self):
        p1 = Produkt.objects.create(model="MM1", stawka=Decimal("10"), grupa_towarowa="AGD", marka="B")
        p2 = Produkt.objects.create(model="MM2", stawka=Decimal("20"), grupa_towarowa="AGD", marka="B")
        task = Task.objects.create(
            nazwa="MixMult",
            typ=Task.Typ.MIX_MNOZNIK,
            prog_mix=3,
            mnoznik_mix=Decimal("1.5"),
            data_od=self.today,
            data_do=self.today,
        )
        task.produkty.set([p1, p2])
        Sprzedaz.objects.create(produkt=p1, liczba_sztuk=1, data_sprzedazy=self.today)
        Sprzedaz.objects.create(produkt=p2, liczba_sztuk=2, data_sprzedazy=self.today)

        response = self.client.get(reverse("produkty:podsumowanie_sprzedazy"))
        summary = response.context["sprzedaz"]
        entry1 = summary[f"{p1.marka}_{p1.model}"]
        entry2 = summary[f"{p2.marka}_{p2.model}"]
        self.assertEqual(entry1["stawka"], Decimal("15"))
        self.assertEqual(entry1["suma_prowizji"], Decimal("15"))
        self.assertEqual(entry2["stawka"], Decimal("30"))
        self.assertEqual(entry2["suma_prowizji"], Decimal("60"))


@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class TaskTypeTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="taskuser", password="pass")
        self.client = Client()
        self.client.login(username="taskuser", password="pass")

    def test_create_mix_prowizja_task(self):
        response = self.client.post(
            reverse("produkty:zadaniowka_dodaj"),
            {
                "nazwa": "Mix prowizja",
                "typ": "MIX_PROWIZJA",
                "prog_mix": 5,
                "premia_za_minimalna_liczbe": "10",
                "data_od": "2024-01-01",
                "data_do": "2024-01-31",
                "mnoznik_stawki": "1.0",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(nazwa="Mix prowizja")
        self.assertEqual(task.typ, Task.Typ.MIX_PROWIZJA)
        self.assertEqual(task.prog_mix, 5)

    def test_create_mix_mnoznik_task(self):
        response = self.client.post(
            reverse("produkty:zadaniowka_dodaj"),
            {
                "nazwa": "Mix mnoznik",
                "typ": "MIX_MNOZNIK",
                "prog_mix": 3,
                "mnoznik_mix": "1.5",
                "data_od": "2024-01-01",
                "data_do": "2024-01-31",
                "mnoznik_stawki": "1.0",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(nazwa="Mix mnoznik")
        self.assertEqual(task.typ, Task.Typ.MIX_MNOZNIK)
        self.assertEqual(task.mnoznik_mix, Decimal("1.5"))

    def test_create_konkretne_modele_task(self):
        response = self.client.post(
            reverse("produkty:zadaniowka_dodaj"),
            {
                "nazwa": "Konkretne modele",
                "typ": "KONKRETNE_MODELE",
                "minimalna_liczba_sztuk": 2,
                "data_od": "2024-01-01",
                "data_do": "2024-01-31",
                "mnoznik_stawki": "1.0",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(nazwa="Konkretne modele")
        self.assertEqual(task.typ, Task.Typ.KONKRETNE_MODELE)
