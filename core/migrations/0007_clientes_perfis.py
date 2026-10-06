import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0006_dados_e_metas"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True, verbose_name="nome")),
                ("active", models.BooleanField(default=True, verbose_name="ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("commodities", models.ManyToManyField(blank=True, related_name="clientes", to="core.commodity", verbose_name="commodities liberadas")),
            ],
            options={"verbose_name": "cliente", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Perfil",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usuarios", to="core.cliente")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="perfil", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name_plural": "perfis"},
        ),
        # etapa 1: campos novos aceitam NULL até a migration de dados preencher
        migrations.AddField("decisao", "cliente", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="decisoes", to="core.cliente")),
        migrations.AddField("meta", "cliente", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="metas", to="core.cliente")),
        migrations.AddField("cenario", "cliente", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="cenarios", to="core.cliente")),
        migrations.AlterField("decisao", "user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="decisoes", to=settings.AUTH_USER_MODEL)),
        migrations.AlterField("meta", "user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="metas", to=settings.AUTH_USER_MODEL)),
    ]
