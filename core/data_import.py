"""Importação de preços mensais por CSV (módulo Dados).

Formato:  commodity,mes,preco     ex.: soja,2026-02,131.40
- `commodity` = slug de uma commodity existente; `mes` = AAAA-MM; `preco` com ponto ou vírgula.
- Tudo ou nada: qualquer erro cancela o arquivo inteiro.
- Mês que era previsão vira histórico (a faixa min/max é descartada), desde que a
  commodity continue com pelo menos 1 mês de previsão.
"""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import Commodity, ImportacaoDados, PrecoMensal

MAX_BYTES = 1_000_000
MAX_ROWS = 5000
HEADER = ["commodity", "mes", "preco"]


class ImportError_(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def parse(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ImportError_(["Arquivo maior que 1 MB."])
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportError_(["O arquivo precisa estar em UTF-8."])
    reader = csv.reader(io.StringIO(text), delimiter=";" if text.split("\n", 1)[0].count(";") else ",")
    rows = list(reader)
    if not rows or [c.strip().lower() for c in rows[0]] != HEADER:
        raise ImportError_([f"Cabeçalho esperado: {','.join(HEADER)}"])
    body = [r for r in rows[1:] if any(c.strip() for c in r)]
    if not body:
        raise ImportError_(["O arquivo não tem linhas de dados."])
    if len(body) > MAX_ROWS:
        raise ImportError_([f"Máximo de {MAX_ROWS} linhas por arquivo."])

    slugs = set(Commodity.objects.values_list("slug", flat=True))
    errors, parsed, seen = [], [], set()
    for n, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        if len(r) != 3:
            errors.append(f"linha {n}: esperado 3 colunas")
            continue
        slug, mes, preco = (c.strip() for c in r)
        try:
            y, m = mes.split("-")
            month = date(int(y), int(m), 1)
            value = Decimal(preco.replace(",", "."))
            if not (Decimal("0.01") <= value <= Decimal("9999999")) or value.as_tuple().exponent < -2:
                raise ValueError
        except (ValueError, InvalidOperation):
            errors.append(f"linha {n}: mês (AAAA-MM) ou preço inválido")
            continue
        if slug not in slugs:
            errors.append(f"linha {n}: commodity '{slug}' não existe")
            continue
        if (slug, month) in seen:
            errors.append(f"linha {n}: {slug} {mes} repetido no arquivo")
            continue
        seen.add((slug, month))
        parsed.append((slug, month, value))
        if len(errors) >= 10:
            break
    if errors:
        raise ImportError_(errors)
    return parsed


@transaction.atomic
def apply(parsed, user, filename):
    commodities = {c.slug: c for c in Commodity.objects.all()}
    created = updated = 0
    for slug, month, value in parsed:
        obj, was_created = PrecoMensal.objects.update_or_create(
            commodity=commodities[slug], month=month,
            defaults={"value": value, "low": None, "high": None, "is_forecast": False},
        )
        created += was_created
        updated += not was_created
    for slug in {p[0] for p in parsed}:
        if not PrecoMensal.objects.filter(commodity=commodities[slug], is_forecast=True).exists():
            raise ImportError_([f"'{slug}' ficaria sem nenhum mês de previsão."])
    return ImportacaoDados.objects.create(
        user=user, filename=filename[:200], created_rows=created, updated_rows=updated
    )
