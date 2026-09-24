from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from .forms import LoginForm
from .telemetry import snapshot


class HowMuchLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html", {"initial": snapshot()})


@login_required
@never_cache
def telemetry_api(request):
    return JsonResponse(snapshot())
