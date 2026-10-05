from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

import json

from decimal import Decimal

from .models import Categoria, Cenario, Commodity, Decisao, Fonte, ImportacaoDados, Leitura, Meta, PontoSerie, PrecoMensal


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


class DadosTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("a", password="x-12345-y", is_staff=True)
        self.user = get_user_model().objects.create_user("u", password="x-12345-y")

    def _upload(self, text, user=None):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(user or self.admin)
        return self.client.post(reverse("data_import"), {"file": SimpleUploadedFile("p.csv", text.encode())})

    def test_importa_novo_atualiza_e_converte_previsao(self):
        self._upload("commodity,mes,preco\nsoja,2026-02,131.40\nsoja,2023-02,100,5\n".replace("100,5", "100.50"))
        soja = Commodity.objects.get(slug="soja")
        fev26 = PrecoMensal.objects.get(commodity=soja, month="2026-02-01")
        self.assertFalse(fev26.is_forecast)
        self.assertIsNone(fev26.low)
        self.assertEqual(PrecoMensal.objects.get(commodity=soja, month="2023-02-01").value, Decimal("100.50"))

    def test_erro_cancela_tudo(self):
        antes = PrecoMensal.objects.count()
        self._upload("commodity,mes,preco\nsoja,2026-02,131.40\nxxx,2026-02,1\n")
        self.assertEqual(PrecoMensal.objects.filter(is_forecast=False).count(), 36 * 4)
        self.assertEqual(PrecoMensal.objects.count(), antes)
        self.assertEqual(ImportacaoDados.objects.count(), 0)

    def test_nao_deixa_commodity_sem_previsao(self):
        linhas = "\n".join(f"soja,2026-{m:02d},100" for m in range(2, 13)) + "\nsoja,2027-01,100"
        self._upload("commodity,mes,preco\n" + linhas)
        self.assertEqual(Commodity.objects.get(slug="soja").precos.filter(is_forecast=True).count(), 12)

    def test_usuario_comum_nao_importa(self):
        self.assertEqual(self._upload("commodity,mes,preco\nsoja,2026-02,1\n", self.user).status_code, 403)

    def test_exportar_e_modelo(self):
        self.client.force_login(self.user)
        body = self.client.get(reverse("data_export")).content.decode("utf-8-sig")
        self.assertTrue(body.startswith("commodity,mes,preco"))
        self.assertEqual(self.client.get(reverse("data_template")).status_code, 200)


class ComparativoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="x-12345-y")
        self.client.force_login(self.user)

    def test_meta_salva_atualiza_e_remove(self):
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "120,50"})
        self.assertEqual(Meta.objects.get().target_price, Decimal("120.50"))
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "99"})
        self.assertEqual(Meta.objects.get().target_price, Decimal("99.00"))
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": ""})
        self.assertEqual(Meta.objects.count(), 0)
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "abc"})
        self.assertEqual(Meta.objects.count(), 0)

    def test_pagina_com_meta_e_compra(self):
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "1"})
        self.client.post(reverse("decision_save"), {"commodity": "soja", "kind": "compra", "month": "2023-02-01", "volume": "10", "price": "1"})
        r = self.client.get(reverse("comparison"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "acima")
        self.assertContains(r, "abaixo do mercado")
