"""Dados iniciais do painel (fictícios, determinísticos).

Fica na migration de propósito: quem rodar `make up` recebe o banco já com
estes registros, igual para todos — nunca um banco vazio. Para mudar/adicionar
dados, crie uma nova migration de dados (não edite esta depois de publicada).
"""

import math
import random
from datetime import datetime, timedelta, timezone

from django.db import migrations

# Âncora fixa: o mesmo banco em qualquer máquina.
END = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)
HISTORY = 48

CATEGORIES = [
    ("Infraestrutura", 58_000, 0.11),
    ("Energia", 34_500, 0.18),
    ("Logística", 41_200, 0.14),
    ("Pessoal", 96_800, 0.04),
    ("Marketing", 27_300, 0.22),
    ("Impostos", 63_900, 0.06),
]
SOURCES = [
    "gateway-sp-01",
    "sensor-energia-04",
    "pdv-rio-12",
    "api-billing",
    "frota-mg-07",
    "nuvem-us-east",
    "estoque-cwb-02",
    "erp-fiscal",
]
KINDS = ("cobrança", "consumo", "reajuste", "conciliação", "provisão", "estorno")


def _status(delta):
    if abs(delta) >= 6:
        return "critico"
    if abs(delta) >= 3:
        return "atencao"
    return "ok"


def seed(apps, schema_editor):
    Categoria = apps.get_model("core", "Categoria")
    Fonte = apps.get_model("core", "Fonte")
    PontoSerie = apps.get_model("core", "PontoSerie")
    Leitura = apps.get_model("core", "Leitura")

    for i in range(HISTORY):
        n = i - (HISTORY - 1)
        rng = random.Random(1000 + i)
        base = 322_000 + 21_000 * math.sin(i / 5.3) + 8_500 * math.sin(i / 0.9)
        PontoSerie.objects.create(
            at=END + STEP * n,
            value=round(base + rng.gauss(0, 1_900), 2),
            readings_per_min=1180 + rng.randint(-90, 140),
        )

    for idx, (name, base, vol) in enumerate(CATEGORIES):
        rng = random.Random(idx)
        Categoria.objects.create(
            name=name,
            value=round(base * (1 + vol * 0.5 * math.sin(idx + 1)) + rng.gauss(0, base * vol * 0.08), 2),
            delta=round(rng.gauss(0, 3.5), 1),
        )

    fontes = [Fonte.objects.create(name=n, online=(n != "estoque-cwb-02")) for n in SOURCES]

    for i in range(16):
        rng = random.Random(i * 7919)
        delta = round(rng.gauss(0, 3.2), 1)
        Leitura.objects.create(
            code=f"#{(i * 37 + 10_001) % 90_000 + 10_000}",
            source=rng.choice(fontes),
            kind=rng.choice(KINDS),
            value=round(abs(rng.gauss(2_400, 1_600)) + 90, 2),
            delta=delta,
            status=_status(delta),
            at=END - timedelta(minutes=7 * i),
        )


def unseed(apps, schema_editor):
    for name in ("Leitura", "PontoSerie", "Categoria", "Fonte"):
        apps.get_model("core", name).objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_schema_inicial")]
    operations = [migrations.RunPython(seed, unseed)]
