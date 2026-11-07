"""Controle de acesso por perfil (Organizador, Caixa, Vendedor).

Para mudar quem acessa o quê, edite só o dicionário ACESSO abaixo.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

ACESSO = {
    # telas (aparecem no menu)
    "dashboard": {"organizador"},
    "vendas": {"organizador", "caixa", "vendedor"},
    "historico": {"organizador", "caixa"},
    "produtos": {"organizador"},
    "estoque": {"organizador", "caixa"},
    "relatorios": {"organizador"},
    "sugestoes": {"organizador"},
    # ações específicas
    "estoque_editar": {"organizador"},
    "venda_cancelar": {"organizador"},
}

ORDEM_MENU = [
    ("dashboard", "Dashboard", "▦"),
    ("vendas", "Nova venda", "＋"),
    ("historico", "Histórico", "☰"),
    ("produtos", "Produtos", "◫"),
    ("estoque", "Estoque", "▤"),
    ("relatorios", "Relatórios", "◔"),
    ("sugestoes", "Sugestões", "✦"),
]


def perfil_do_usuario(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "organizador"
    nomes = set(user.groups.values_list("name", flat=True))
    for perfil in ("organizador", "caixa", "vendedor"):
        if perfil.capitalize() in nomes:
            return perfil
    return None


def pode(user, chave):
    return perfil_do_usuario(user) in ACESSO.get(chave, set())


def acesso(chave):
    """Decorator: exige login e que o perfil do usuário tenha acesso à 'chave'."""

    def decorador(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not pode(request.user, chave):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorador
