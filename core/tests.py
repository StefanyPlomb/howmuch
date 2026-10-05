from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

import json

from .models import Categoria, Cenario, Commodity, Fonte, Leitura, PontoSerie, PrecoMensal


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


class PlataformaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="x-12345-y")

    def test_commodities_semeadas_com_historico_e_previsao(self):
        self.assertGreaterEqual(Commodity.objects.count(), 4)
        for c in Commodity.objects.all():
            self.assertEqual(c.precos.filter(is_forecast=False).count(), 36)
            self.assertEqual(c.precos.filter(is_forecast=True).count(), 12)

    def test_home_publica_e_paginas_internas_protegidas(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        for name in ("dashboard", "forecasts", "scenarios"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        self.client.force_login(self.user)
        for name in ("dashboard", "forecasts", "scenarios"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_salvar_cenario_recalcula_no_servidor(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("scenario_save"),
            json.dumps({"commodity": "soja", "price_shock": 10, "volume": 1000, "hedge": 50, "name": "t"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        c = Cenario.objects.get()
        self.assertAlmostEqual(float(c.scenario_cost / c.baseline_cost), 1.05, places=4)

    def test_salvar_cenario_rejeita_valores_invalidos(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("scenario_save"),
            json.dumps({"commodity": "soja", "price_shock": 999, "volume": 1, "hedge": 50}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
