import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Avg
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .decisions import evaluate
from .forms import DecisaoForm, LoginForm
from .models import Cenario, Commodity, Decisao, PrecoMensal
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


@login_required
def decisions(request):
    commodities = list(Commodity.objects.all())
    months = list(
        PrecoMensal.objects.filter(is_forecast=False).order_by("-month")
        .values_list("month", flat=True).distinct()[:24]
    )
    rows, total, decided, wins = [], Decimal(0), 0, 0
    for d in Decisao.objects.filter(user=request.user).select_related("commodity"):
        ref, gain = evaluate(d)
        rows.append({"d": d, "ref": ref, "gain": gain})
        if gain is not None:
            total += gain
            decided += 1
            wins += gain > 0
    return render(request, "core/decisions.html", {
        "active": "decisions",
        "commodities": commodities,
        "months": months,
        "rows": rows,
        "total_gain": total,
        "decided": decided,
        "hit_rate": round(wins / decided * 100) if decided else None,
        "open_count": len(rows) - decided,
    })


@login_required
@require_POST
def decision_save(request):
    form = DecisaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Confira os campos: " + "; ".join(f"{k}" for k in form.errors))
        return redirect("decisions")
    cd = form.cleaned_data
    commodity = get_object_or_404(Commodity, slug=cd["commodity"])
    month = cd["month"].replace(day=1)
    market = PrecoMensal.objects.filter(commodity=commodity, month=month, is_forecast=False).first()
    if market is None:
        messages.error(request, "Escolha um mês do histórico.")
        return redirect("decisions")
    Decisao.objects.create(
        user=request.user, commodity=commodity, kind=cd["kind"], month=month,
        volume=cd["volume"], price=cd["price"] or market.value, note=cd["note"],
    )
    messages.success(request, "Decisão registrada.")
    return redirect("decisions")


@login_required
@require_POST
def decision_delete(request, pk):
    get_object_or_404(Decisao, pk=pk, user=request.user).delete()
    return redirect("decisions")
