from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

import json

from .models import Categoria, Cenario, Commodity, Decisao, Fonte, Leitura, PontoSerie, PrecoMensal


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


class DecisoesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="x-12345-y")
        self.client.force_login(self.user)

    def _post(self, **kw):
        data = {"commodity": "soja", "kind": "compra", "month": "2023-02-01", "volume": "100", "price": "1000"}
        data.update(kw)
        return self.client.post(reverse("decision_save"), data)

    def test_compra_cara_da_prejuizo_e_venda_cara_da_ganho(self):
        from .decisions import evaluate

        self._post(kind="compra", price="1000")
        self._post(kind="venda", price="1000")
        compra, venda = Decisao.objects.order_by("id")
        self.assertLess(evaluate(compra)[1], 0)
        self.assertGreater(evaluate(venda)[1], 0)

    def test_decisao_recente_fica_em_aberto(self):
        from .decisions import evaluate

        ultimo = PrecoMensal.objects.filter(commodity__slug="soja", is_forecast=False).latest("month").month
        self._post(month=ultimo.isoformat())
        self.assertEqual(evaluate(Decisao.objects.get()), (None, None))

    def test_preco_vazio_usa_mercado_e_mes_de_previsao_e_recusado(self):
        self._post(price="")
        mercado = PrecoMensal.objects.get(commodity__slug="soja", month="2023-02-01").value
        self.assertEqual(Decisao.objects.get().price, mercado)
        self._post(month="2026-06-01")
        self.assertEqual(Decisao.objects.count(), 1)

    def test_pagina_e_isolamento_entre_usuarios(self):
        self._post()
        outro = get_user_model().objects.create_user("o", password="x-12345-y")
        self.client.force_login(outro)
        self.assertEqual(self.client.get(reverse("decisions")).status_code, 200)
        self.assertEqual(self.client.post(reverse("decision_delete", args=[Decisao.objects.get().pk])).status_code, 404)
