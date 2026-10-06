"""Cálculo do cenário (ScenarioLab). O JS de cenarios.js espelha esta fórmula.

custo_base     = volume × preço médio previsto (12 meses)
custo_cenário  = custo_base × (hedge + (1 − hedge) × (1 + choque))
A parcela protegida (hedge) fica travada no preço previsto; o resto sofre o choque.
"""

from decimal import Decimal


def simulate(avg_price, volume, shock_pct, hedge_pct):
    base = Decimal(avg_price) * Decimal(volume)
    hedge = Decimal(hedge_pct) / 100
    shock = Decimal(shock_pct) / 100
    scenario = base * (hedge + (1 - hedge) * (1 + shock))
    return base.quantize(Decimal("0.01")), scenario.quantize(Decimal("0.01"))
