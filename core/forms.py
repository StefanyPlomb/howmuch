from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "seu usuário",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "••••••••"}
        ),
    )

    error_messages = {
        "invalid_login": "Usuário ou senha incorretos. Confira e tente novamente.",
        "inactive": "Esta conta está desativada.",
    }
