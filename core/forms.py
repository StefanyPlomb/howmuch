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


class DecisaoForm(forms.Form):
    commodity = forms.SlugField()
    kind = forms.ChoiceField(choices=[("compra", "Compra"), ("venda", "Venda")])
    month = forms.DateField(input_formats=["%Y-%m-%d"])
    volume = forms.DecimalField(min_value=0.01, max_value=10**9, decimal_places=2)
    price = forms.DecimalField(min_value=0.01, max_value=10**7, decimal_places=2, required=False)
    note = forms.CharField(max_length=200, required=False)
