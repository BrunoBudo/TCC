from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_grupos(sender, **kwargs):
    """Cria os 3 perfis de acesso automaticamente depois do migrate."""
    from django.contrib.auth.models import Group

    for nome in ("Organizador", "Caixa", "Vendedor"):
        Group.objects.get_or_create(name=nome)


class PainelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "painel"

    def ready(self):
        post_migrate.connect(criar_grupos, sender=self)
