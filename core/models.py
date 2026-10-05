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
