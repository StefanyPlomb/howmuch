"""Papéis e escopo de dados.

- administrador = `is_staff`: cadastra tudo; pode "ver como" um cliente (cliente ativo na sessão).
- cliente = usuário com `Perfil`: só visualiza o que o administrador liberou para o seu
  cliente e pode fazer simulações (Cenários).
"""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .models import Cliente, Commodity

SESSION_KEY = "cliente_ativo"


def current_cliente(request):
    user = request.user
    if user.is_staff:
        pk = request.session.get(SESSION_KEY)
        return Cliente.objects.filter(pk=pk).first() if pk else None
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.cliente.active:
        return perfil.cliente
    return None


def visible_commodities(request):
    """Commodities que o usuário pode ver agora (cliente: as liberadas; admin: todas, ou as do cliente ativo)."""
    qs = Commodity.objects.ready()
    cliente = current_cliente(request)
    if cliente:
        return qs.filter(clientes=cliente)
    return qs if request.user.is_staff else qs.none()


def admin_required(view):
    @wraps(view)
    def wrapper(request, *a, **kw):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise PermissionDenied
        return view(request, *a, **kw)

    return wrapper


def render_empty(request, active, title):
    return render(request, "core/empty.html", {"active": active, "title": title})
