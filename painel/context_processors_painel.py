from meutcc.permissoes import ACESSO, ORDEM_MENU, perfil_do_usuario, pode
from vendas.models import Festa
from .sugestoes import gerar_sugestoes


def menu(request):
    """Disponibiliza o menu (já filtrado pelo perfil) em todos os templates."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    perfil = perfil_do_usuario(user)
    festa = Festa.atual()

    # Utiliza a função pode() para validar permissões corretamente (incluindo is_superuser e is_staff)
    itens = [
        {"url": chave, "nome": nome, "icone": icone, "badge": 0}
        for chave, nome, icone in ORDEM_MENU
        if pode(user, chave)
    ]

    if perfil == "organizador":
        total = len(gerar_sugestoes(festa))
        for item in itens:
            if item["url"] == "sugestoes":
                item["badge"] = total

    return {
        "menu": itens,
        "perfil": perfil,
        "festa_atual": festa,
        # O dicionário 'pode' agora usa a função pode() para que o HTML libere superusers e staff
        "pode": {chave: pode(user, chave) for chave in ACESSO},
    }