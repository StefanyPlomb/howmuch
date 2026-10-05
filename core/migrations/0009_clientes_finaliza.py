import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0008_clientes_demo"),
    ]

    operations = [
        migrations.RemoveConstraint("meta", "meta_unica"),
        migrations.RemoveField("meta", "user"),
        migrations.AlterField("meta", "cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metas", to="core.cliente")),
        migrations.AddConstraint("meta", models.UniqueConstraint(fields=("cliente", "commodity"), name="meta_unica")),
        migrations.AlterField("decisao", "cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decisoes", to="core.cliente")),
        migrations.RenameField("decisao", "user", "created_by"),
        migrations.AlterField("decisao", "created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
    ]
