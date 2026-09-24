import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria o superusuário inicial (ADMIN_USER/ADMIN_EMAIL/ADMIN_PASSWORD do .env). Idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Redefine a senha se o usuário já existir.",
        )

    def handle(self, *args, **opts):
        username = os.environ.get("ADMIN_USER")
        email = os.environ.get("ADMIN_EMAIL", "")
        password = os.environ.get("ADMIN_PASSWORD")
        if not username or not password:
            raise CommandError("Defina ADMIN_USER e ADMIN_PASSWORD no .env.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created or opts["reset_password"]:
            user.set_password(password)
            user.is_staff = user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Superusuário '{username}' {'criado' if created else 'atualizado'}."
            ))
        else:
            self.stdout.write(f"Superusuário '{username}' já existe — nada a fazer.")
