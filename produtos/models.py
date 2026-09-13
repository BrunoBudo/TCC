from django.db import models

class Produto(models.Model):
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

    class Meta:
        ordering = ["nome"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome