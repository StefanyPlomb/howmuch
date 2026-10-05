from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Fonte, Leitura, PontoSerie


class SeedDataTests(TestCase):
    """As migrations devem entregar o banco já com registros."""

    def test_migrations_populam_o_banco(self):
        self.assertGreaterEqual(PontoSerie.objects.count(), 48)
        self.assertGreater(Categoria.objects.count(), 0)
        self.assertGreater(Fonte.objects.count(), 0)
        self.assertGreaterEqual(Leitura.objects.count(), 8)


class ViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="x-12345-y")

    def test_dashboard_exige_login(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("telemetry")).status_code, 302)

    def test_api_devolve_dados_do_banco(self):
        self.client.force_login(self.user)
        data = self.client.get(reverse("telemetry")).json()
        self.assertEqual(len(data["series"]), 48)
        self.assertEqual(len(data["feed"]), 8)
        self.assertEqual(data["kpis"]["sources_online"], Fonte.objects.filter(online=True).count())
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
