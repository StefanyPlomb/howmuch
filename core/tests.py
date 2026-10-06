import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .decisions import evaluate
from .models import (
    Categoria, Cenario, Cliente, Commodity, Decisao, Fonte, ImportacaoDados, Leitura, Meta, Perfil,
    PontoSerie, PrecoMensal,
)

User = get_user_model()
PWD = "x-12345-y"


def make_admin(name="adm"):
    return User.objects.create_user(name, password=PWD, is_staff=True)


def make_client_user(cliente, name="cli"):
    u = User.objects.create_user(name, password=PWD)
    Perfil.objects.create(user=u, cliente=cliente)
    return u


class Base(TestCase):
    def setUp(self):
        self.soja = Commodity.objects.get(slug="soja")
        self.milho = Commodity.objects.get(slug="milho")
        self.cafe = Commodity.objects.get(slug="cafe")
        # clientes de demonstração criados pelas migrations
        self.a = Cliente.objects.get(name="Cooperativa Horizonte")   # soja, milho
        self.b = Cliente.objects.get(name="Frigorífico Aurora")      # boi gordo, café
        self.admin = make_admin()
        self.user_a = make_client_user(self.a, "ua")
        self.user_b = make_client_user(self.b, "ub")

    def as_admin(self, cliente=None):
        self.client.force_login(self.admin)
        if cliente:
            self.client.post(reverse("cliente_ativo"), {"cliente": cliente.pk})


class SeedDataTests(TestCase):
    """As migrations devem entregar o banco já com registros."""

    def test_migrations_populam_o_banco(self):
        self.assertGreaterEqual(PontoSerie.objects.count(), 48)
        self.assertGreater(Categoria.objects.count(), 0)
        self.assertGreater(Fonte.objects.count(), 0)
        self.assertGreaterEqual(Leitura.objects.count(), 8)
        self.assertEqual(Commodity.objects.ready().count(), 4)
        for c in Commodity.objects.all():
            self.assertEqual(c.precos.filter(is_forecast=False).count(), 36)
            self.assertEqual(c.precos.filter(is_forecast=True).count(), 12)

    def test_clientes_demo_vem_com_metas_e_decisoes_mas_sem_usuarios(self):
        self.assertEqual(Cliente.objects.count(), 2)
        for c in Cliente.objects.all():
            self.assertGreater(c.commodities.count(), 0)
            self.assertGreater(c.metas.count(), 0)
            self.assertGreater(c.decisoes.count(), 0)
            self.assertEqual(c.usuarios.count(), 0)


class PapeisTests(Base):
    def test_paginas_internas_exigem_login(self):
        for name in ("dashboard", "forecasts", "scenarios", "decisions", "comparison", "data", "admin_home"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

    def test_cliente_nao_acessa_dados_nem_administracao(self):
        self.client.force_login(self.user_a)
        for name in ("data", "admin_home", "data_export", "data_template"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.assertEqual(self.client.post(reverse("data_import")).status_code, 403)
        self.assertEqual(self.client.post(reverse("cliente_create"), {"name": "x"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("cliente_ativo"), {"cliente": self.b.pk}).status_code, 403)

    def test_cliente_nao_registra_decisao_nem_meta(self):
        self.client.force_login(self.user_a)
        d = {"commodity": "soja", "kind": "compra", "month": "2023-02-01", "volume": "1", "price": "1"}
        self.assertEqual(self.client.post(reverse("decision_save"), d).status_code, 403)
        self.assertEqual(self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "1"}).status_code, 403)
        pk = self.a.decisoes.first().pk
        self.assertEqual(self.client.post(reverse("decision_delete", args=[pk])).status_code, 403)
        self.assertTrue(Decisao.objects.filter(pk=pk).exists())

    def test_cliente_ve_so_as_commodities_liberadas(self):
        self.client.force_login(self.user_a)
        r = self.client.get(reverse("forecasts"))
        self.assertContains(r, "Soja")
        self.assertContains(r, "Milho")
        self.assertNotContains(r, "Café arábica")
        # tentar abrir uma não liberada cai na primeira liberada
        r = self.client.get(reverse("forecasts") + "?c=cafe")
        self.assertEqual(r.context["current"].slug, "soja")

    def test_cliente_so_ve_os_proprios_dados(self):
        self.client.force_login(self.user_a)
        r = self.client.get(reverse("decisions"))
        self.assertEqual({row["d"].cliente for row in r.context["rows"]}, {self.a})
        self.assertFalse(r.context["can_edit"])
        self.assertNotContains(r, "Nova decisão")
        r = self.client.get(reverse("comparison"))
        self.assertEqual({row["commodity"].slug for row in r.context["rows"]}, {"soja", "milho"})

    def test_cliente_sem_perfil_ou_inativo_ve_vazio(self):
        sem = User.objects.create_user("sem", password=PWD)
        self.client.force_login(sem)
        self.assertContains(self.client.get(reverse("forecasts")), "Ainda não há conteúdo")
        self.a.active = False
        self.a.save()
        self.client.force_login(self.user_a)
        self.assertContains(self.client.get(reverse("comparison")), "Ainda não há conteúdo")


class CenariosTests(Base):
    def _save(self, **kw):
        body = {"commodity": "soja", "price_shock": 10, "volume": 1000, "hedge": 50, "name": "t"}
        body.update(kw)
        return self.client.post(reverse("scenario_save"), json.dumps(body), content_type="application/json")

    def test_cliente_simula_e_salva_para_o_proprio_cliente(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self._save().status_code, 200)
        c = Cenario.objects.get()
        self.assertEqual(c.cliente, self.a)
        self.assertAlmostEqual(float(c.scenario_cost / c.baseline_cost), 1.05, places=4)

    def test_cliente_nao_simula_commodity_nao_liberada(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self._save(commodity="cafe").status_code, 400)
        self.assertEqual(Cenario.objects.count(), 0)

    def test_valores_invalidos_e_isolamento_entre_clientes(self):
        self.client.force_login(self.user_a)
        self.assertEqual(self._save(price_shock=999).status_code, 400)
        self._save()
        self.client.force_login(self.user_b)
        r = self.client.get(reverse("scenarios"))
        self.assertEqual(len(r.context["saved"]), 0)


class AdminOperaTests(Base):
    def test_ver_como_cliente_e_registrar_decisao_e_meta(self):
        self.as_admin(self.a)
        d = {"commodity": "soja", "kind": "compra", "month": "2023-02-01", "volume": "100", "price": ""}
        antes = self.a.decisoes.count()
        self.client.post(reverse("decision_save"), d)
        nova = self.a.decisoes.latest("created_at")
        self.assertEqual(self.a.decisoes.count(), antes + 1)
        self.assertEqual(nova.created_by, self.admin)
        self.assertEqual(nova.price, PrecoMensal.objects.get(commodity=self.soja, month="2023-02-01").value)
        # commodity não liberada para o cliente é recusada
        self.client.post(reverse("decision_save"), {**d, "commodity": "cafe"})
        self.assertEqual(self.a.decisoes.count(), antes + 1)
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": "120,50"})
        self.assertEqual(Meta.objects.get(cliente=self.a, commodity=self.soja).target_price, Decimal("120.50"))
        self.client.post(reverse("meta_save"), {"commodity": "soja", "target": ""})
        self.assertFalse(Meta.objects.filter(cliente=self.a, commodity=self.soja).exists())
        self.client.post(reverse("decision_delete", args=[nova.pk]))
        self.assertEqual(self.a.decisoes.count(), antes)

    def test_sem_cliente_ativo_nao_registra(self):
        self.as_admin()
        d = {"commodity": "soja", "kind": "compra", "month": "2023-02-01", "volume": "1", "price": "1"}
        n = Decisao.objects.count()
        self.client.post(reverse("decision_save"), d)
        self.assertEqual(Decisao.objects.count(), n)

    def test_decisao_de_outro_cliente_nao_e_apagada(self):
        self.as_admin(self.a)
        pk = self.b.decisoes.first().pk
        self.assertEqual(self.client.post(reverse("decision_delete", args=[pk])).status_code, 404)

    def test_compra_cara_da_prejuizo_e_venda_cara_da_ganho_e_recente_fica_em_aberto(self):
        from datetime import date

        mk = lambda kind, month, price: Decisao.objects.create(
            cliente=self.a, commodity=self.soja, kind=kind, month=month, volume=100, price=price)
        self.assertLess(evaluate(mk("compra", date(2023, 2, 1), 1000))[1], 0)
        self.assertGreater(evaluate(mk("venda", date(2023, 2, 1), 1000))[1], 0)
        ultimo = PrecoMensal.objects.filter(commodity=self.soja, is_forecast=False).latest("month").month
        self.assertEqual(evaluate(mk("compra", ultimo, 100)), (None, None))

    def test_comparativo_usa_decisoes_do_cliente(self):
        self.a.decisoes.all().delete()
        from datetime import date

        Decisao.objects.create(cliente=self.a, commodity=self.soja, kind="compra", month=date(2023, 2, 1), volume=10, price=1)
        self.as_admin(self.a)
        r = self.client.get(reverse("comparison"))
        self.assertContains(r, "abaixo do mercado")


class AdministracaoTests(Base):
    def setUp(self):
        super().setUp()
        self.as_admin()

    def test_criar_cliente_liberar_commodities_e_criar_usuario(self):
        r = self.client.post(reverse("cliente_create"), {"name": "Novo"})
        novo = Cliente.objects.get(name="Novo")
        self.assertRedirects(r, reverse("admin_cliente", args=[novo.pk]))
        self.client.post(reverse("cliente_update", args=[novo.pk]), {"name": "Novo", "active": "on", "commodities": [self.soja.pk]})
        self.assertEqual(list(novo.commodities.all()), [self.soja])
        self.client.post(reverse("usuario_create", args=[novo.pk]), {"username": "joao", "password": "Senha-forte-123"})
        u = User.objects.get(username="joao")
        self.assertFalse(u.is_staff)
        self.assertEqual(u.perfil.cliente, novo)
        # o usuário criado enxerga só o que foi liberado
        self.client.logout()
        self.assertTrue(self.client.login(username="joao", password="Senha-forte-123"))
        r = self.client.get(reverse("forecasts"))
        self.assertEqual([c.slug for c in r.context["commodities"]], ["soja"])

    def test_senha_fraca_ou_usuario_repetido_e_recusado(self):
        url = reverse("usuario_create", args=[self.a.pk])
        self.client.post(url, {"username": "fraco", "password": "123"})
        self.client.post(url, {"username": "ua", "password": "Senha-forte-123"})
        self.assertFalse(User.objects.filter(username="fraco").exists())
        self.assertEqual(User.objects.filter(username__iexact="ua").count(), 1)

    def test_redefinir_senha_e_remover_so_dentro_do_proprio_cliente(self):
        self.client.post(reverse("usuario_password", args=[self.a.pk, self.user_a.pk]), {"password": "Outra-senha-987"})
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password("Outra-senha-987"))
        # usuário do cliente B pela URL do cliente A -> 404
        self.assertEqual(self.client.post(reverse("usuario_delete", args=[self.a.pk, self.user_b.pk])).status_code, 404)
        self.client.post(reverse("usuario_delete", args=[self.a.pk, self.user_a.pk]))
        self.assertFalse(User.objects.filter(pk=self.user_a.pk).exists())

    def test_excluir_cliente_exige_nome_e_leva_usuarios(self):
        url = reverse("cliente_delete", args=[self.a.pk])
        self.client.post(url, {"confirm": "errado"})
        self.assertTrue(Cliente.objects.filter(pk=self.a.pk).exists())
        self.client.post(url, {"confirm": "Cooperativa Horizonte"})
        self.assertFalse(Cliente.objects.filter(pk=self.a.pk).exists())
        self.assertFalse(User.objects.filter(pk=self.user_a.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_criar_commodity_sem_serie_nao_aparece_para_cliente(self):
        self.client.post(reverse("commodity_create"), {"name": "Trigo", "unit": "tonelada", "description": ""})
        trigo = Commodity.objects.get(slug="trigo")
        self.a.commodities.add(trigo)
        self.client.force_login(self.user_a)
        r = self.client.get(reverse("forecasts"))
        self.assertNotIn(trigo, r.context["commodities"])


class DadosTests(Base):
    def _upload(self, text, user=None):
        self.client.force_login(user or self.admin)
        return self.client.post(reverse("data_import"), {"file": SimpleUploadedFile("p.csv", text.encode())})

    def test_importa_novo_atualiza_e_converte_previsao(self):
        self._upload("commodity,mes,preco\nsoja,2026-02,131.40\nsoja,2023-02,100.50\n")
        fev26 = PrecoMensal.objects.get(commodity=self.soja, month="2026-02-01")
        self.assertFalse(fev26.is_forecast)
        self.assertIsNone(fev26.low)
        self.assertEqual(PrecoMensal.objects.get(commodity=self.soja, month="2023-02-01").value, Decimal("100.50"))

    def test_formato_completo_cadastra_serie_de_commodity_nova(self):
        Commodity.objects.create(slug="trigo", name="Trigo", unit="t")
        linhas = ["trigo,2025-01,10,historico,,", "trigo,2025-02,11,historico,,", "trigo,2025-03,12,previsao,11,13"]
        self._upload("commodity,mes,preco,tipo,minimo,maximo\n" + "\n".join(linhas))
        self.assertTrue(Commodity.objects.ready().filter(slug="trigo").exists())
        p = PrecoMensal.objects.get(commodity__slug="trigo", month="2025-03-01")
        self.assertTrue(p.is_forecast)
        self.assertEqual((p.low, p.high), (Decimal("11"), Decimal("13")))

    def test_exportacao_pode_ser_reimportada(self):
        self.client.force_login(self.admin)
        body = self.client.get(reverse("data_export")).content.decode("utf-8-sig")
        antes = PrecoMensal.objects.count()
        self._upload(body)
        self.assertEqual(PrecoMensal.objects.count(), antes)
        self.assertEqual(PrecoMensal.objects.filter(is_forecast=True).count(), 48)

    def test_erro_cancela_tudo(self):
        antes = PrecoMensal.objects.count()
        self._upload("commodity,mes,preco\nsoja,2026-02,131.40\nxxx,2026-02,1\n")
        self.assertEqual(PrecoMensal.objects.filter(is_forecast=False).count(), 36 * 4)
        self.assertEqual(PrecoMensal.objects.count(), antes)
        self.assertEqual(ImportacaoDados.objects.count(), 0)

    def test_nao_deixa_commodity_sem_previsao(self):
        linhas = "\n".join(f"soja,2026-{m:02d},100" for m in range(2, 13)) + "\nsoja,2027-01,100"
        self._upload("commodity,mes,preco\n" + linhas)
        self.assertEqual(self.soja.precos.filter(is_forecast=True).count(), 12)

    def test_exportar_e_modelo_para_admin(self):
        self.client.force_login(self.admin)
        body = self.client.get(reverse("data_export")).content.decode("utf-8-sig")
        self.assertTrue(body.startswith("commodity,mes,preco"))
        self.assertEqual(self.client.get(reverse("data_template")).status_code, 200)


class HomeTests(TestCase):
    def test_home_publica(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
