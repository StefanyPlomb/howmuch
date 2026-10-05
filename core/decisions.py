"""Avaliação de decisões (módulo Decisões).

Referência de mercado = média dos 3 meses seguintes ao mês da decisão (só dados
históricos). Se ainda não há 3 meses de histórico depois, a decisão fica "em aberto".

  compra: ganho = (referência − preço fechado) × volume   (comprou mais barato = ganho)
  venda : ganho = (preço fechado − referência) × volume   (vendeu mais caro   = ganho)
"""

from decimal import Decimal

from .models import Decisao, PrecoMensal

WINDOW = 3


def _add_months(d, n):
    m = d.month - 1 + n
    return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)


def reference_price(commodity, month):
    months = [_add_months(month, i) for i in range(1, WINDOW + 1)]
    vals = list(
        PrecoMensal.objects.filter(commodity=commodity, month__in=months, is_forecast=False)
        .values_list("value", flat=True)
    )
    if len(vals) < WINDOW:
        return None
    return sum(vals) / len(vals)


def evaluate(decision):
    """Devolve (preço de referência, ganho) ou (None, None) se em aberto."""
    ref = reference_price(decision.commodity, decision.month)
    if ref is None:
        return None, None
    diff = (ref - decision.price) if decision.kind == Decisao.Tipo.COMPRA else (decision.price - ref)
    return ref.quantize(Decimal("0.01")), (diff * decision.volume).quantize(Decimal("0.01"))
