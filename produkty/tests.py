from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Produkt, Sprzedaz


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

