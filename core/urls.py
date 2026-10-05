from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.HowMuchLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("app/", views.dashboard, name="dashboard"),
    path("app/previsoes/", views.forecasts, name="forecasts"),
    path("app/cenarios/", views.scenarios, name="scenarios"),
    path("app/cenarios/salvar/", views.save_scenario, name="scenario_save"),
    path("app/decisoes/", views.decisions, name="decisions"),
    path("app/decisoes/salvar/", views.decision_save, name="decision_save"),
    path("app/decisoes/<int:pk>/excluir/", views.decision_delete, name="decision_delete"),
    path("api/telemetria/", views.telemetry_api, name="telemetry"),
]
