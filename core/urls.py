from django.contrib.auth.views import LogoutView
from django.urls import path

from . import admin_views, views

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
    path("app/dados/", views.data_page, name="data"),
    path("app/dados/importar/", views.data_import_view, name="data_import"),
    path("app/dados/exportar.csv", views.data_export, name="data_export"),
    path("app/dados/modelo.csv", views.data_template, name="data_template"),
    path("app/comparativo/", views.comparison_page, name="comparison"),
    path("app/comparativo/meta/", views.meta_save, name="meta_save"),
    path("app/cliente-ativo/", views.set_cliente_ativo, name="cliente_ativo"),
    path("app/admin/", admin_views.admin_home, name="admin_home"),
    path("app/admin/clientes/novo/", admin_views.cliente_create, name="cliente_create"),
    path("app/admin/clientes/<int:pk>/", admin_views.cliente_detail, name="admin_cliente"),
    path("app/admin/clientes/<int:pk>/salvar/", admin_views.cliente_update, name="cliente_update"),
    path("app/admin/clientes/<int:pk>/excluir/", admin_views.cliente_delete, name="cliente_delete"),
    path("app/admin/clientes/<int:pk>/usuarios/novo/", admin_views.usuario_create, name="usuario_create"),
    path("app/admin/clientes/<int:pk>/usuarios/<int:user_pk>/senha/", admin_views.usuario_password, name="usuario_password"),
    path("app/admin/clientes/<int:pk>/usuarios/<int:user_pk>/excluir/", admin_views.usuario_delete, name="usuario_delete"),
    path("app/admin/commodities/nova/", admin_views.commodity_create, name="commodity_create"),
    path("api/telemetria/", views.telemetry_api, name="telemetry"),
]
