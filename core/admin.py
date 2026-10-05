from django.contrib import admin

from .models import Categoria, Fonte, Leitura, PontoSerie

admin.site.register(Categoria)
admin.site.register(Fonte)
admin.site.register(PontoSerie)


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = ("code", "source", "kind", "value", "delta", "status", "at")
    list_filter = ("status", "source")
