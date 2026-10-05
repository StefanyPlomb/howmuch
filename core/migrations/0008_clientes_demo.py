"""Clientes de demonstração, com commodities liberadas, metas e decisões já cadastradas.

Os usuários dos clientes NÃO são criados aqui (senha não vai para o repositório):
o administrador cria em Administração → Clientes.
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

# nome do cliente -> (commodities liberadas, metas {slug: teto}, decisões [(slug, tipo, mês, volume, preço fechado|None, nota)])
DEMO = {
    "Cooperativa Horizonte": (
        ["soja", "milho"],
        {"soja": "125.00", "milho": "64.00"},
        [
            ("soja", "venda", date(2024, 3, 1), 8000, None, "Venda antecipada da safra"),
            ("soja", "compra", date(2024, 9, 1), 3000, None, "Insumo para o plantio"),
            ("milho", "venda", date(2025, 1, 1), 12000, None, "Liberou caixa antes da entressafra"),
            ("milho", "compra", date(2025, 8, 1), 5000, 66.00, "Reposição de estoque"),
        ],
    ),
    "Frigorífico Aurora": (
        ["boi-gordo", "cafe"],
        {"boi-gordo": "340.00", "cafe": "1250.00"},
        [
            ("boi-gordo", "compra", date(2024, 6, 1), 2500, None, "Lote para abate"),
            ("boi-gordo", "compra", date(2025, 4, 1), 3200, 335.00, "Contrato mensal"),
            ("cafe", "venda", date(2024, 11, 1), 900, None, "Fechou antes da alta"),
            ("cafe", "compra", date(2025, 10, 1), 600, None, "Reposição"),
        ],
    ),
}


def seed(apps, schema_editor):
    Commodity = apps.get_model("core", "Commodity")
    Cliente = apps.get_model("core", "Cliente")
    Meta = apps.get_model("core", "Meta")
    Decisao = apps.get_model("core", "Decisao")
    Preco = apps.get_model("core", "PrecoMensal")

    # Decisões/metas antigas eram por usuário e não têm cliente: não há como mapear.
    Decisao.objects.filter(cliente__isnull=True).delete()
    Meta.objects.filter(cliente__isnull=True).delete()

    for name, (slugs, metas, decisoes) in DEMO.items():
        cliente = Cliente.objects.create(name=name)
        by_slug = {c.slug: c for c in Commodity.objects.filter(slug__in=slugs)}
        cliente.commodities.set(by_slug.values())
        for slug, target in metas.items():
            if slug in by_slug:
                Meta.objects.create(cliente=cliente, commodity=by_slug[slug], target_price=Decimal(target))
        for slug, kind, month, volume, price, note in decisoes:
            c = by_slug.get(slug)
            market = Preco.objects.filter(commodity=c, month=month, is_forecast=False).first() if c else None
            if not market:
                continue
            Decisao.objects.create(
                cliente=cliente, commodity=c, kind=kind, month=month, volume=Decimal(volume),
                price=Decimal(str(price)) if price is not None else market.value, note=note,
            )


def unseed(apps, schema_editor):
    apps.get_model("core", "Cliente").objects.filter(name__in=DEMO).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0007_clientes_perfis")]
    operations = [migrations.RunPython(seed, unseed)]
