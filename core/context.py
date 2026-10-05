from .access import current_cliente
from .models import Cliente


def access(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "is_admin": request.user.is_staff,
        "cliente_atual": current_cliente(request),
        "clientes_all": Cliente.objects.all() if request.user.is_staff else [],
    }
