"""Commodities, histórico (36 meses) e previsão (12 meses) fictícios e determinísticos."""

import math
import random
from datetime import date

from django.db import migrations

# (slug, nome, unidade, descrição, preço base, volatilidade, tendência anual, sazonalidade)
COMMODITIES = [
    ("soja", "Soja", "saca 60 kg", "Grão — referência de exportação", 128.0, 0.05, 0.04, 0.06),
    ("milho", "Milho", "saca 60 kg", "Grão — ração e etanol", 62.0, 0.07, 0.02, 0.09),
    ("boi-gordo", "Boi gordo", "arroba", "Pecuária de corte", 305.0, 0.03, 0.06, 0.04),
    ("cafe", "Café arábica", "saca 60 kg", "Soft commodity de alta volatilidade", 1280.0, 0.09, 0.05, 0.11),
]
HIST = 36
FUT = 12
START = (2023, 2)  # primeiro mês do histórico


def _month(i):
    y, m = START[0], START[1] + i
    return date(y + (m - 1) // 12, (m - 1) % 12 + 1, 1)


def seed(apps, schema_editor):
    Commodity = apps.get_model("core", "Commodity")
    Preco = apps.get_model("core", "PrecoMensal")

    for idx, (slug, name, unit, desc, base, vol, trend, season) in enumerate(COMMODITIES):
        Commodity.objects.create(slug=slug, name=name, unit=unit, description=desc)
        c = Commodity.objects.get(slug=slug)
        rng = random.Random(500 + idx)
        level = base
        rows = []
        for i in range(HIST + FUT):
            seasonal = 1 + season * math.sin(2 * math.pi * (i % 12) / 12 + idx)
            drift = 1 + trend * i / 12
            if i < HIST:
                level *= 1 + rng.gauss(0, vol * 0.35)
                value = level * seasonal * 0.5 + base * drift * seasonal * 0.5
                rows.append(Preco(commodity=c, month=_month(i), value=round(value, 2)))
            else:
                h = i - HIST + 1
                value = base * drift * seasonal * (1 + 0.01 * math.sqrt(h) * rng.uniform(-1, 2))
                band = value * vol * 0.55 * math.sqrt(h) / 2
                rows.append(Preco(
                    commodity=c, month=_month(i), value=round(value, 2),
                    low=round(value - band, 2), high=round(value + band, 2), is_forecast=True,
                ))
        Preco.objects.bulk_create(rows)


def unseed(apps, schema_editor):
    apps.get_model("core", "Cenario").objects.all().delete()
    apps.get_model("core", "PrecoMensal").objects.all().delete()
    apps.get_model("core", "Commodity").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0003_plataforma_previsao")]
    operations = [migrations.RunPython(seed, unseed)]
