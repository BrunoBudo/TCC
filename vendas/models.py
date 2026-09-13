from django.db import models
from django.contrib.auth.models import User
from produtos.models import Produto


class Venda(models.Model):
    data_hora = models.DateTimeField(auto_now_add=True)
    operador = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"

    def __str__(self):
        return f"Venda #{self.id} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    def calcular_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.valor_total = total
        self.save(update_fields=["valor_total"])
        return total


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, related_name="itens", on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario