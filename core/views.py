import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Avg
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import LoginForm
from .models import Cenario, Commodity
from .scenarios import simulate
from .telemetry import snapshot


class HowMuchLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def home(request):
    """Página pública de apresentação da plataforma (produtos/módulos)."""
    return render(request, "core/home.html", {"commodities": Commodity.objects.all()})


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {"initial": snapshot(), "active": "dashboard"})


@login_required
@never_cache
def telemetry_api(request):
    return JsonResponse(snapshot())


def _series(commodity):
    return [
        {
            "month": p.month.isoformat(),
            "value": float(p.value),
            "low": float(p.low) if p.low is not None else None,
            "high": float(p.high) if p.high is not None else None,
            "forecast": p.is_forecast,
        }
        for p in commodity.precos.all()
    ]


def _pick(request):
    commodities = list(Commodity.objects.all())
    if not commodities:
        raise Http404
    slug = request.GET.get("c")
    current = next((c for c in commodities if c.slug == slug), commodities[0])
    return commodities, current


@login_required
def forecasts(request):
    commodities, current = _pick(request)
    series = _series(current)
    return render(request, "core/forecasts.html", {
        "active": "forecasts",
        "commodities": commodities,
        "current": current,
        "series": series,
        "initial": {"unit": current.unit, "series": series},
    })


def _avg_forecast(commodity):
    return commodity.precos.filter(is_forecast=True).aggregate(a=Avg("value"))["a"]


@login_required
def scenarios(request):
    commodities, current = _pick(request)
    return render(request, "core/scenarios.html", {
        "active": "scenarios",
        "commodities": commodities,
        "current": current,
        "saved": Cenario.objects.filter(user=request.user).select_related("commodity")[:10],
        "initial": {
            "unit": current.unit,
            "avg_price": float(_avg_forecast(current)),
            "last": float(current.precos.filter(is_forecast=False).last().value),
        },
    })


@login_required
@require_POST
def save_scenario(request):
    try:
        body = json.loads(request.body)
        commodity = Commodity.objects.get(slug=body["commodity"])
        shock = Decimal(str(body["price_shock"]))
        volume = Decimal(str(body["volume"]))
        hedge = int(body["hedge"])
        name = str(body.get("name") or "").strip()[:80] or f"Cenário {commodity.name}"
    except (ValueError, KeyError, TypeError, InvalidOperation, Commodity.DoesNotExist):
        return JsonResponse({"error": "Dados inválidos."}, status=400)
    if not (-50 <= shock <= 100 and 0 <= hedge <= 100 and 0 < volume <= Decimal("1e9")):
        return JsonResponse({"error": "Valores fora do intervalo permitido."}, status=400)

    base, scen = simulate(_avg_forecast(commodity), volume, shock, hedge)
    c = Cenario.objects.create(
        user=request.user, commodity=commodity, name=name, price_shock=shock,
        volume=volume, hedge=hedge, baseline_cost=base, scenario_cost=scen,
    )
    return JsonResponse({
        "id": c.id, "name": c.name, "commodity": commodity.name, "price_shock": float(shock),
        "hedge": hedge, "baseline": float(base), "scenario": float(scen), "impact": float(c.impact),
    })
