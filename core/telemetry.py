"""Snapshot do dashboard, lido do banco (Postgres).

Nada é gerado em memória: séries, categorias e leituras são registros das
tabelas de `core`, criados pelas migrations (schema + dados iniciais).
"""

from django.utils import timezone

from .models import Categoria, Fonte, Leitura, PontoSerie

HISTORY = 48
FEED = 8


def _f(dec):
    return float(dec)


def snapshot():
    points = list(PontoSerie.objects.order_by("-at")[:HISTORY])[::-1]
    feed = list(Leitura.objects.select_related("source").order_by("-at")[:FEED])
    categories = list(Categoria.objects.all())

    series = [{"t": int(p.at.timestamp()), "v": _f(p.value)} for p in points]
    values = [p["v"] for p in series]
    current, first = values[-1], values[0]
    previous = values[-2] if len(values) > 1 else current

    return {
        "generated_at": timezone.now().timestamp(),
        "kpis": {
            "total": current,
            "total_delta": round((current - previous) / previous * 100, 2),
            "window_delta": round((current - first) / first * 100, 2),
            "hourly_cost": round(current / 720, 2),
            "peak": max(values),
            "low": min(values),
            "readings_per_min": points[-1].readings_per_min,
            "alerts": sum(1 for f in feed if f.status != Leitura.Status.OK),
            "sources_online": Fonte.objects.filter(online=True).count(),
        },
        "series": series,
        "categories": [
            {"name": c.name, "value": _f(c.value), "delta": _f(c.delta)} for c in categories
        ],
        "feed": [
            {
                "id": f.code,
                "source": f.source.name,
                "kind": f.kind,
                "value": _f(f.value),
                "delta": _f(f.delta),
                "status": f.status,
                "at": int(f.at.timestamp()),
            }
            for f in feed
        ],
    }
