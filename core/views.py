import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db.models import Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from . import comparison, data_import
from .access import SESSION_KEY, admin_required, current_cliente, render_empty, visible_commodities
from .decisions import evaluate
from .forms import DecisaoForm, LoginForm
from .models import Cenario, Cliente, Commodity, Decisao, ImportacaoDados, Meta, PrecoMensal
from .scenarios import simulate
from .telemetry import snapshot


class HowMuchLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def home(request):
    """Página pública de apresentação da plataforma (produtos/módulos)."""
    return render(request, "core/home.html", {"commodities": Commodity.objects.ready()})


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
    commodities = list(visible_commodities(request))
    if not commodities:
        return [], None
    slug = request.GET.get("c")
    return commodities, next((c for c in commodities if c.slug == slug), commodities[0])


@login_required
def forecasts(request):
    commodities, current = _pick(request)
    if not current:
        return render_empty(request, "forecasts", "Previsões")
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
    if not current:
        return render_empty(request, "scenarios", "Cenários")
    cliente = current_cliente(request)
    saved = Cenario.objects.filter(cliente=cliente) if cliente else Cenario.objects.filter(cliente=None, user=request.user)
    return render(request, "core/scenarios.html", {
        "active": "scenarios",
        "commodities": commodities,
        "current": current,
        "saved": saved.select_related("commodity")[:10],
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
        commodity = visible_commodities(request).get(slug=body["commodity"])
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
        user=request.user, cliente=current_cliente(request), commodity=commodity, name=name, price_shock=shock,
        volume=volume, hedge=hedge, baseline_cost=base, scenario_cost=scen,
    )
    return JsonResponse({
        "id": c.id, "name": c.name, "commodity": commodity.name, "price_shock": float(shock),
        "hedge": hedge, "baseline": float(base), "scenario": float(scen), "impact": float(c.impact),
    })


@login_required
def decisions(request):
    cliente = current_cliente(request)
    if not cliente:
        return render_empty(request, "decisions", "Decisões")
    commodities = list(Commodity.objects.ready().filter(clientes=cliente))
    months = list(
        PrecoMensal.objects.filter(is_forecast=False, commodity__in=commodities).order_by("-month")
        .values_list("month", flat=True).distinct()[:24]
    )
    rows, total, decided, wins = [], Decimal(0), 0, 0
    for d in Decisao.objects.filter(cliente=cliente).select_related("commodity"):
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
        "can_edit": request.user.is_staff,
        "total_gain": total,
        "decided": decided,
        "hit_rate": round(wins / decided * 100) if decided else None,
        "open_count": len(rows) - decided,
    })


@login_required
@admin_required
@require_POST
def decision_save(request):
    cliente = current_cliente(request)
    if not cliente:
        messages.error(request, "Escolha um cliente no topo da página antes de registrar.")
        return redirect("decisions")
    form = DecisaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Confira os campos: " + "; ".join(f"{k}" for k in form.errors))
        return redirect("decisions")
    cd = form.cleaned_data
    commodity = Commodity.objects.ready().filter(slug=cd["commodity"], clientes=cliente).first()
    if commodity is None:
        messages.error(request, "Essa commodity não está liberada para o cliente.")
        return redirect("decisions")
    month = cd["month"].replace(day=1)
    market = PrecoMensal.objects.filter(commodity=commodity, month=month, is_forecast=False).first()
    if market is None:
        messages.error(request, "Escolha um mês do histórico.")
        return redirect("decisions")
    Decisao.objects.create(
        cliente=cliente, created_by=request.user, commodity=commodity, kind=cd["kind"], month=month,
        volume=cd["volume"], price=cd["price"] or market.value, note=cd["note"],
    )
    messages.success(request, "Decisão registrada.")
    return redirect("decisions")


@login_required
@admin_required
@require_POST
def decision_delete(request, pk):
    cliente = current_cliente(request)
    get_object_or_404(Decisao, pk=pk, cliente=cliente).delete()
    return redirect("decisions")


# ---------------------------------------------------------------- Dados
@login_required
@admin_required
def data_page(request):
    inventory = []
    for c in Commodity.objects.all():
        hist = c.precos.filter(is_forecast=False)
        fc = c.precos.filter(is_forecast=True)
        inventory.append({
            "c": c, "hist": hist.count(), "fc": fc.count(),
            "first": hist.first().month if hist.exists() else None,
            "last": hist.last().month if hist.exists() else None,
        })
    return render(request, "core/data.html", {
        "active": "data",
        "inventory": inventory,
        "imports": ImportacaoDados.objects.select_related("user")[:10],
    })


@login_required
@admin_required
@require_POST
def data_import_view(request):
    f = request.FILES.get("file")
    if not f:
        messages.error(request, "Escolha um arquivo CSV.")
        return redirect("data")
    try:
        parsed = data_import.parse(f.read(data_import.MAX_BYTES + 1))
        imp = data_import.apply(parsed, request.user, f.name)
    except data_import.ImportError_ as e:
        messages.error(request, "Importação cancelada — " + " · ".join(e.errors))
        return redirect("data")
    messages.success(request, f"Importado: {imp.created_rows} novos e {imp.updated_rows} atualizados.")
    return redirect("data")


def _csv_response(name):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    resp.write("\ufeff")
    return resp


@login_required
@admin_required
def data_export(request):
    resp = _csv_response("howmuch_precos.csv")
    w = csv.writer(resp)
    w.writerow(["commodity", "mes", "preco", "tipo", "minimo", "maximo"])
    for p in PrecoMensal.objects.select_related("commodity"):
        w.writerow([p.commodity.slug, p.month.strftime("%Y-%m"), p.value,
                    "previsao" if p.is_forecast else "historico", p.low or "", p.high or ""])
    return resp


@login_required
@admin_required
def data_template(request):
    resp = _csv_response("modelo_importacao.csv")
    w = csv.writer(resp)
    w.writerow(data_import.HEADER)
    w.writerow(["soja", "2026-02", "131.40"])
    return resp


# ---------------------------------------------------------- Comparativo
@login_required
def comparison_page(request):
    commodities = list(visible_commodities(request))
    if not commodities:
        return render_empty(request, "comparison", "Comparativo")
    cliente = current_cliente(request)
    return render(request, "core/comparison.html", {
        "active": "comparison",
        "rows": comparison.build(cliente, commodities),
        "can_edit": request.user.is_staff and cliente is not None,
        "initial": {"series": comparison.index_series(commodities)},
    })


@login_required
@admin_required
@require_POST
def meta_save(request):
    cliente = current_cliente(request)
    if not cliente:
        messages.error(request, "Escolha um cliente no topo da página antes de definir metas.")
        return redirect("comparison")
    commodity = get_object_or_404(Commodity.objects.ready(), slug=request.POST.get("commodity", ""), clientes=cliente)
    raw = request.POST.get("target", "").strip().replace(",", ".")
    if not raw:
        Meta.objects.filter(cliente=cliente, commodity=commodity).delete()
        messages.success(request, f"Meta de {commodity.name} removida.")
        return redirect("comparison")
    try:
        target = Decimal(raw)
        if not (Decimal("0.01") <= target <= Decimal("9999999")):
            raise InvalidOperation
        target = target.quantize(Decimal("0.01"))
    except InvalidOperation:
        messages.error(request, "Preço-alvo inválido.")
        return redirect("comparison")
    Meta.objects.update_or_create(cliente=cliente, commodity=commodity, defaults={"target_price": target})
    messages.success(request, f"Meta de {commodity.name} salva.")
    return redirect("comparison")


# ------------------------------------------------- "ver como" (administrador)
@login_required
@admin_required
@require_POST
def set_cliente_ativo(request):
    pk = request.POST.get("cliente", "")
    if pk and Cliente.objects.filter(pk=pk).exists():
        request.session[SESSION_KEY] = int(pk)
    else:
        request.session.pop(SESSION_KEY, None)
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/app/") else "dashboard")
