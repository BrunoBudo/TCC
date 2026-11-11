from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from vendas.models import Festa

PERFIS = [("Organizador", "Organizador"), ("Caixa", "Caixa"), ("Vendedor", "Vendedor")]
FORMATO_DATA = "%Y-%m-%dT%H:%M"  # formato do campo <input type="datetime-local">
_FORMATOS = [FORMATO_DATA, "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"]


class FestaForm(forms.ModelForm):
    inicio = forms.DateTimeField(input_formats=_FORMATOS)
    fim = forms.DateTimeField(input_formats=_FORMATOS)

    class Meta:
        model = Festa
        fields = ["nome", "inicio", "fim", "ativa"]

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("inicio"), dados.get("fim")
        if inicio and fim and fim <= inicio:
            self.add_error("fim", "O fim da festa precisa ser depois do início.")
        return dados


class UsuarioForm(forms.Form):
    """Cria ou edita um usuário. Na edição o nome de usuário não muda e a senha é opcional."""

    username = forms.CharField(max_length=150, required=False)
    first_name = forms.CharField(max_length=150, required=False)
    perfil = forms.ChoiceField(choices=PERFIS)
    senha = forms.CharField(required=False)

    def __init__(self, *args, instancia=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instancia = instancia

    def clean_username(self):
        if self.instancia:
            return self.instancia.username
        nome = (self.cleaned_data.get("username") or "").strip()
        if not nome:
            raise ValidationError("Informe o nome de usuário.")
        User.username_validator(nome)
        if User.objects.filter(username__iexact=nome).exists():
            raise ValidationError("Já existe um usuário com esse nome.")
        return nome

    def clean_senha(self):
        senha = self.cleaned_data.get("senha") or ""
        if not senha:
            if not self.instancia:
                raise ValidationError("Informe uma senha.")
            return ""
        usuario = self.instancia or User(username=self.cleaned_data.get("username", ""))
        validate_password(senha, user=usuario)
        return senha
