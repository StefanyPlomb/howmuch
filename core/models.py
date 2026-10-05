from django.conf import settings
from django.db import models


class Categoria(models.Model):
    name = models.CharField("nome", max_length=60, unique=True)
    value = models.DecimalField("valor", max_digits=14, decimal_places=2)
    delta = models.DecimalField("variação (%)", max_digits=5, decimal_places=1)

    class Meta:
        verbose_name = "categoria"
        ordering = ["-value"]

    def __str__(self):
        return self.name


class Fonte(models.Model):
    name = models.CharField("nome", max_length=60, unique=True)
    online = models.BooleanField(default=True)

    class Meta:
        verbose_name = "fonte"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PontoSerie(models.Model):
    at = models.DateTimeField("momento", unique=True)
    value = models.DecimalField("valor total", max_digits=14, decimal_places=2)
    readings_per_min = models.PositiveIntegerField("leituras por minuto")

    class Meta:
        verbose_name = "ponto da série"
        verbose_name_plural = "pontos da série"
        ordering = ["at"]

    def __str__(self):
        return f"{self.at:%d/%m/%Y %H:%M} · {self.value}"


class Leitura(models.Model):
    class Status(models.TextChoices):
        OK = "ok", "Normal"
        ATENCAO = "atencao", "Atenção"
        CRITICO = "critico", "Crítico"

    code = models.CharField("código", max_length=12, unique=True)
    source = models.ForeignKey(Fonte, on_delete=models.PROTECT, related_name="leituras")
    kind = models.CharField("tipo", max_length=30)
    value = models.DecimalField("valor", max_digits=14, decimal_places=2)
    delta = models.DecimalField("variação (%)", max_digits=5, decimal_places=1)
    status = models.CharField(max_length=10, choices=Status.choices)
    at = models.DateTimeField("momento")

    class Meta:
        verbose_name_plural = "leituras"
        ordering = ["-at"]

    def __str__(self):
        return f"{self.code} · {self.source}"


class Commodity(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField("nome", max_length=60)
    unit = models.CharField("unidade", max_length=30)
    description = models.CharField("descrição", max_length=200, blank=True)

    class Meta:
        verbose_name = "commodity"
        verbose_name_plural = "commodities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PrecoMensal(models.Model):
    """Preço histórico (is_forecast=False) ou previsão com banda low/high."""

    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name="precos")
    month = models.DateField("mês")
    value = models.DecimalField("preço", max_digits=12, decimal_places=2)
    low = models.DecimalField("mínimo previsto", max_digits=12, decimal_places=2, null=True, blank=True)
    high = models.DecimalField("máximo previsto", max_digits=12, decimal_places=2, null=True, blank=True)
    is_forecast = models.BooleanField("é previsão", default=False)

    class Meta:
        verbose_name = "preço mensal"
        verbose_name_plural = "preços mensais"
        ordering = ["commodity", "month"]
        constraints = [models.UniqueConstraint(fields=["commodity", "month"], name="preco_unico_por_mes")]

    def __str__(self):
        return f"{self.commodity} · {self.month:%m/%Y}"


class Cenario(models.Model):
    """Simulação salva: choque de preço + volume + % protegido (hedge)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cenarios")
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name="cenarios")
    name = models.CharField("nome", max_length=80)
    price_shock = models.DecimalField("choque de preço (%)", max_digits=5, decimal_places=1)
    volume = models.DecimalField("volume (12 meses)", max_digits=14, decimal_places=2)
    hedge = models.PositiveSmallIntegerField("proteção/hedge (%)")
    baseline_cost = models.DecimalField("custo base", max_digits=16, decimal_places=2)
    scenario_cost = models.DecimalField("custo no cenário", max_digits=16, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cenário"
        ordering = ["-created_at"]

    @property
    def impact(self):
        return self.scenario_cost - self.baseline_cost

    def __str__(self):
        return self.name
