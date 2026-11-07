from django.conf import settings
from django.db import models
from django.utils import timezone


class Produto(models.Model):
    itens_venda: models.QuerySet
    CATEGORIA_CHOICES = [
        ("alimento", "Alimento"),
        ("bebida", "Bebida"),
        ("outro", "Outro"),
    ]

    nome = models.CharField(max_length=100)
    categoria = models.CharField(
        max_length=20, choices=CATEGORIA_CHOICES, default="outro"
    )
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    quantidade_estoque = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # --- campos novos (alertas de estoque e sugestões) ---
    estoque_minimo = models.PositiveIntegerField(default=10)
    esgotou_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome

    @property
    def status(self):
        if self.quantidade_estoque == 0:
            return "esgotado"
        if self.quantidade_estoque <= self.estoque_minimo:
            return "baixo"
        return "normal"

    @property
    def status_classe(self):
        return {"esgotado": "out", "baixo": "low", "normal": "ok"}[self.status]

    @property
    def status_rotulo(self):
        return {"esgotado": "Esgotado", "baixo": "Baixo", "normal": "Normal"}[self.status]

    @property
    def nivel_pct(self):
        if not self.estoque_minimo:
            return 100 if self.quantidade_estoque else 0
        return min(100, int(self.quantidade_estoque / (self.estoque_minimo * 3) * 100))


class MovimentacaoEstoque(models.Model):
    """Histórico de tudo que entra e sai do estoque (aparece nos Relatórios)."""

    TIPOS = [("entrada", "Entrada"), ("saida", "Venda"), ("estorno", "Estorno")]

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="movimentacoes")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    quantidade = models.IntegerField(help_text="Positivo entra no estoque, negativo sai.")
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    motivo = models.CharField(max_length=200, blank=True)
    criada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "Movimentação de estoque"
        verbose_name_plural = "Movimentações de estoque"
