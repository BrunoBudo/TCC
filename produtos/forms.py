from django import forms

from .models import Produto


class ProdutoForm(forms.ModelForm):
    estoque_inicial = forms.IntegerField(min_value=0, required=False)

    class Meta:
        model = Produto
        fields = ["nome", "categoria", "preco", "estoque_minimo"]
