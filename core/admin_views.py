"""Área de Administração (só administrador): clientes, usuários dos clientes e commodities."""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .access import SESSION_KEY, admin_required
from .models import Cliente, Commodity, Perfil

User = get_user_model()


class ClienteForm(forms.Form):
    name = forms.CharField(max_length=80)


class UsuarioForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(strip=False)

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Já existe um usuário com esse nome.")
        return u

    def clean_password(self):
        validate_password(self.cleaned_data["password"])
        return self.cleaned_data["password"]


class CommodityForm(forms.Form):
    name = forms.CharField(max_length=60)
    unit = forms.CharField(max_length=30)
    description = forms.CharField(max_length=200, required=False)


def _errors(form):
    return " · ".join(m for errs in form.errors.values() for m in errs)


@login_required
@admin_required
def admin_home(request):
    return render(request, "core/admin_home.html", {
        "active": "admin",
        "clientes": Cliente.objects.prefetch_related("commodities").all(),
        "commodities": Commodity.objects.annotate(
            n_hist=Count("precos", filter=Q(precos__is_forecast=False)),
            n_fc=Count("precos", filter=Q(precos__is_forecast=True)),
        ),
    })


@login_required
@admin_required
@require_POST
def cliente_create(request):
    form = ClienteForm(request.POST)
    name = form.cleaned_data["name"].strip() if form.is_valid() else ""
    if not name:
        messages.error(request, "Informe o nome do cliente.")
        return redirect("admin_home")
    try:
        c = Cliente.objects.create(name=name)
    except IntegrityError:
        messages.error(request, "Já existe um cliente com esse nome.")
        return redirect("admin_home")
    messages.success(request, f"Cliente '{c.name}' criado. Libere as commodities e crie os usuários.")
    return redirect("admin_cliente", pk=c.pk)


@login_required
@admin_required
def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, "core/admin_cliente.html", {
        "active": "admin",
        "cl": cliente,
        "all_commodities": Commodity.objects.all(),
        "liberadas": set(cliente.commodities.values_list("pk", flat=True)),
        "usuarios": cliente.usuarios.select_related("user"),
    })


@login_required
@admin_required
@require_POST
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    name = request.POST.get("name", "").strip()[:80]
    if name and name != cliente.name:
        if Cliente.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, "Já existe um cliente com esse nome.")
            return redirect("admin_cliente", pk=pk)
        cliente.name = name
    cliente.active = request.POST.get("active") == "on"
    cliente.save()
    cliente.commodities.set(Commodity.objects.filter(pk__in=request.POST.getlist("commodities")))
    messages.success(request, "Cliente atualizado.")
    return redirect("admin_cliente", pk=pk)


@login_required
@admin_required
@require_POST
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.POST.get("confirm") != cliente.name:
        messages.error(request, "Para excluir, digite o nome exato do cliente.")
        return redirect("admin_cliente", pk=pk)
    with transaction.atomic():
        User.objects.filter(perfil__cliente=cliente).delete()
        cliente.delete()
    if request.session.get(SESSION_KEY) == pk:
        request.session.pop(SESSION_KEY, None)
    messages.success(request, "Cliente excluído (com usuários, decisões, metas e cenários).")
    return redirect("admin_home")


@login_required
@admin_required
@require_POST
def usuario_create(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = UsuarioForm(request.POST)
    if not form.is_valid():
        messages.error(request, _errors(form))
        return redirect("admin_cliente", pk=pk)
    with transaction.atomic():
        user = User.objects.create_user(form.cleaned_data["username"], password=form.cleaned_data["password"])
        Perfil.objects.create(user=user, cliente=cliente)
    messages.success(request, f"Usuário '{user.username}' criado para {cliente.name}.")
    return redirect("admin_cliente", pk=pk)


def _client_user(pk, user_pk):
    perfil = get_object_or_404(Perfil.objects.select_related("user"), user_id=user_pk, cliente_id=pk)
    return perfil.user


@login_required
@admin_required
@require_POST
def usuario_password(request, pk, user_pk):
    user = _client_user(pk, user_pk)
    pwd = request.POST.get("password", "")
    try:
        validate_password(pwd, user)
    except ValidationError as e:
        messages.error(request, " · ".join(e.messages))
        return redirect("admin_cliente", pk=pk)
    user.set_password(pwd)
    user.save()
    messages.success(request, f"Senha de '{user.username}' redefinida.")
    return redirect("admin_cliente", pk=pk)


@login_required
@admin_required
@require_POST
def usuario_delete(request, pk, user_pk):
    user = _client_user(pk, user_pk)
    user.delete()
    messages.success(request, "Usuário removido.")
    return redirect("admin_cliente", pk=pk)


@login_required
@admin_required
@require_POST
def commodity_create(request):
    form = CommodityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Informe nome e unidade.")
        return redirect("admin_home")
    cd = form.cleaned_data
    slug = slugify(cd["name"])
    if not slug or Commodity.objects.filter(slug=slug).exists():
        messages.error(request, "Já existe uma commodity com esse nome.")
        return redirect("admin_home")
    Commodity.objects.create(slug=slug, name=cd["name"].strip(), unit=cd["unit"].strip(), description=cd["description"].strip())
    messages.success(request, f"Commodity criada (slug: {slug}). Importe os preços em Dados para ela aparecer nas telas.")
    return redirect("admin_home")
