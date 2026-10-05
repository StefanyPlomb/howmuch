"""Comparativo: cada commodity contra o mercado, as metas e as decisões do usuário."""

from decimal import Decimal

from django.db.models import Avg

from .models import Decisao, Meta


def _wavg(pairs):
    vol = sum(v for _, v in pairs)
    return sum(p * v for p, v in pairs) / vol if vol else None


def build(cliente, commodities):
    metas = {m.commodity_id: m.target_price for m in Meta.objects.filter(cliente=cliente)} if cliente else {}
    rows = []
    for c in commodities:
        hist = list(c.precos.filter(is_forecast=False).order_by("month"))
        last = hist[-1].value
        year_ago = hist[-13].value if len(hist) > 12 else hist[0].value
        avg12 = sum(p.value for p in hist[-12:]) / len(hist[-12:])
        fc_avg = c.precos.filter(is_forecast=True).aggregate(a=Avg("value"))["a"]
        target = metas.get(c.id)

        # benchmark do usuário: preço médio das compras vs. mercado nos mesmos meses
        market = {p.month: p.value for p in hist}
        compras = [d for d in Decisao.objects.filter(cliente=cliente, commodity=c, kind=Decisao.Tipo.COMPRA) if d.month in market] if cliente else []
        mine = _wavg([(d.price, d.volume) for d in compras])
        mkt = _wavg([(market[d.month], d.volume) for d in compras])

        rows.append({
            "commodity": c,
            "last": last,
            "year_delta": float((last - year_ago) / year_ago * 100),
            "avg12": avg12,
            "forecast_avg": fc_avg,
            "forecast_delta": float((fc_avg - last) / last * 100),
            "target": target,
            "target_gap": float((last - target) / target * 100) if target else None,
            "over_target": bool(target and last > target),
            "my_avg": mine,
            "market_avg": mkt,
            "my_vs_market": float((mine - mkt) / mkt * 100) if mine and mkt else None,
        })
    return rows


def index_series(commodities):
    """Série base 100 (primeiro mês) de cada commodity, para comparar variações."""
    out = []
    for c in commodities:
        pts = list(c.precos.all())
        base = float(pts[0].value)
        out.append({
            "name": c.name,
            "points": [{"month": p.month.isoformat(), "v": round(float(p.value) / base * 100, 2), "forecast": p.is_forecast} for p in pts],
        })
    return out
