from django.contrib import admin

from .models import Categoria, Cenario, Cliente, Decisao, Perfil, ImportacaoDados, Meta, Commodity, Fonte, Leitura, PontoSerie, PrecoMensal

admin.site.register(Categoria)
admin.site.register(Fonte)
admin.site.register(PontoSerie)


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = ("code", "source", "kind", "value", "delta", "status", "at")
    list_filter = ("status", "source")
admin.site.register(Commodity)
admin.site.register(Cenario)


@admin.register(PrecoMensal)
class PrecoMensalAdmin(admin.ModelAdmin):
    list_display = ("commodity", "month", "value", "low", "high", "is_forecast")
    list_filter = ("commodity", "is_forecast")
admin.site.register(Decisao)
admin.site.register(ImportacaoDados)
admin.site.register(Meta)
admin.site.register(Cliente)
admin.site.register(Perfil)
