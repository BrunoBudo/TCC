from django.db import models

from vendas.models import Festa


class SugestaoDispensada(models.Model):
    """Guarda as sugestões que o organizador clicou em 'Dispensar'."""

    festa = models.ForeignKey(Festa, on_delete=models.CASCADE)
    chave = models.CharField(max_length=80)

    class Meta:
        unique_together = ("festa", "chave")
