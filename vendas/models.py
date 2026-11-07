from decimal import Decimal
from django.db import models
from typing import Callable
from django.contrib.auth.models import User
from django.utils import timezone
from produtos.models import Produto


class Festa(models.Model):
    """A festa em andamento. As sugestões usam o horário dela para os cálculos."""
    
    nome = models.CharField(max_length=150)
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    ativa = models.BooleanField(default=True, help_text="Só uma festa fica ativa por vez.")

    class Meta:
        ordering = ["-inicio"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.ativa:
            Festa.objects.exclude(pk=self.pk).update(ativa=False)

    @classmethod
    def atual(cls):
        return cls.objects.filter(ativa=True).first()

    def progresso(self, momento=None):
        """Quanto da festa já passou (0 a 1)."""
        momento = momento or timezone.now()
        total = (self.fim - self.inicio).total_seconds()
        if total <= 0:
            return 1.0
        decorrido = (momento - self.inicio).total_seconds()
        return max(0.0, min(1.0, decorrido / total))


class Venda(models.Model):
    itens: models.QuerySet['ItemVenda']
    get_forma_pagamento_display: Callable[[], str]
    FORMAS = [("dinheiro", "Dinheiro"), ("pix", "Pix"), ("cartao", "Cartão")]

    data_hora = models.DateTimeField(auto_now_add=True)
    operador = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    # --- campos novos ---
    festa = models.ForeignKey(Festa, null=True, blank=True, on_delete=models.PROTECT, related_name="vendas")
    forma_pagamento = models.CharField(max_length=10, choices=FORMAS, default="dinheiro")
    cancelada = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Venda"
        verbose_name_plural = "Vendas" 

    def __str__(self):
        id_str = self.pk if self.pk else "Nova"
        data_str = self.data_hora.strftime('%d/%m/%Y %H:%M') if self.data_hora else "Sem data"
        return f"Venda #{id_str} - {data_str}"

    def calcular_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.valor_total = total
        self.save(update_fields=["valor_total"])
        return total
    
class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, related_name="itens", on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, related_name="itens_venda", on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario