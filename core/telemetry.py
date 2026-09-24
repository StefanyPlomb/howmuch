"""Gerador de telemetria FALSA de valores para o dashboard.

Os números são determinísticos por "tick" (janela de TICK_SECONDS), então
todos os clientes enxergam a mesma série e o gráfico é contínuo entre polls.
"""

import math
import random
import time

TICK_SECONDS = 3
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

MOMENTS = ("cobrança", "consumo", "reajuste", "conciliação", "provisão", "estorno")


def _tick(now=None):
    return int((now if now is not None else time.time()) // TICK_SECONDS)


def _total_at(tick):
    rng = random.Random(tick)
    base = 322_000 + 21_000 * math.sin(tick / 53) + 8_500 * math.sin(tick / 9)
    return base + rng.gauss(0, 1_900)


def _category_at(tick, idx, base, vol):
    rng = random.Random(tick * 31 + idx)
    drift = math.sin(tick / (17 + idx * 5) + idx)
    return base * (1 + vol * 0.5 * drift) + rng.gauss(0, base * vol * 0.08)


def _status(delta):
    if abs(delta) >= 6:
        return "critico"
    if abs(delta) >= 3:
        return "atencao"
    return "ok"


def snapshot(now=None):
    now = now if now is not None else time.time()
    tick = _tick(now)

    series = [
        {"t": (tick - i) * TICK_SECONDS, "v": round(_total_at(tick - i), 2)}
        for i in range(HISTORY - 1, -1, -1)
    ]
    current = series[-1]["v"]
    previous = series[-2]["v"]
    first = series[0]["v"]
    peak = max(p["v"] for p in series)
    low = min(p["v"] for p in series)

    categories = []
    for idx, (name, base, vol) in enumerate(CATEGORIES):
        now_v = _category_at(tick, idx, base, vol)
        before = _category_at(tick - 20, idx, base, vol)
        categories.append(
            {
                "name": name,
                "value": round(now_v, 2),
                "delta": round((now_v - before) / before * 100, 1),
            }
        )
    categories.sort(key=lambda c: c["value"], reverse=True)

    feed = []
    for i in range(8):
        tk = tick - i
        rng = random.Random(tk * 7919)
        delta = round(rng.gauss(0, 3.2), 1)
        feed.append(
            {
                "id": f"#{(tk * 37) % 90000 + 10000}",
                "source": rng.choice(SOURCES),
                "kind": rng.choice(MOMENTS),
                "value": round(abs(rng.gauss(2_400, 1_600)) + 90, 2),
                "delta": delta,
                "status": _status(delta),
                "at": tk * TICK_SECONDS,
            }
        )

    alerts = sum(1 for f in feed if f["status"] != "ok")

    return {
        "generated_at": now,
        "kpis": {
            "total": current,
            "total_delta": round((current - previous) / previous * 100, 2),
            "window_delta": round((current - first) / first * 100, 2),
            "hourly_cost": round(current / 720, 2),
            "peak": round(peak, 2),
            "low": round(low, 2),
            "readings_per_min": 1180 + random.Random(tick).randint(-90, 140),
            "alerts": alerts,
            "sources_online": 47 - int(tick % 3 == 0),
        },
        "series": series,
        "categories": categories,
        "feed": feed,
    }
