"""Telas de gestão (só o Organizador): Festas e Usuários."""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from meutcc.permissoes import acesso, perfil_do_usuario
from vendas.models import Festa

from .forms import FORMATO_DATA, FestaForm, UsuarioForm


def _erros(form):
    return " ".join(erro for lista in form.errors.values() for erro in lista)


# ------------------------------------------------------------------ Festas
@acesso("festas")
def festas(request):
    lista = Festa.objects.annotate(n_vendas=Count("vendas", filter=Q(vendas__cancelada=False)))
    linhas = [
        {
            "festa": f,
            "inicio_input": timezone.localtime(f.inicio).strftime(FORMATO_DATA),
            "fim_input": timezone.localtime(f.fim).strftime(FORMATO_DATA),
        }
        for f in lista
    ]
    return render(request, "painel/festas.html", {"linhas": linhas})


@acesso("festas")
@require_POST
def festa_salvar(request):
    pk = request.POST.get("id")
    instancia = get_object_or_404(Festa, pk=pk) if pk else None
    form = FestaForm(request.POST, instance=instancia)
    if not form.is_valid():
        messages.error(request, "Não foi possível salvar a festa. " + _erros(form))
        return redirect("festas")
    form.save()  # Festa.save() desativa as outras quando esta fica ativa
    messages.success(request, "Festa salva.")
    return redirect("festas")


@acesso("festas")
@require_POST
def festa_ativar(request, pk):
    festa = get_object_or_404(Festa, pk=pk)
    festa.ativa = True
    festa.save()
    messages.success(request, "A festa \"{}\" agora é a festa ativa.".format(festa.nome))
    return redirect("festas")


@acesso("festas")
@require_POST
def festa_excluir(request, pk):
    festa = get_object_or_404(Festa, pk=pk)
    if festa.vendas.exists():
        messages.error(request, "Não dá para excluir uma festa que já tem vendas. Deixe-a inativa, se preferir.")
    else:
        festa.delete()
        messages.success(request, "Festa excluída.")
    return redirect("festas")


# ---------------------------------------------------------------- Usuários
def _outros_organizadores_ativos(excluir_pk):
    return (
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name="Organizador"))
        .exclude(pk=excluir_pk)
        .distinct()
        .exists()
    )


@acesso("usuarios")
def usuarios(request):
    linhas = []
    for u in User.objects.order_by("username"):
        perfil = perfil_do_usuario(u)
        linhas.append({
            "usuario": u,
            "perfil": perfil,
            "perfil_nome": perfil.capitalize() if perfil else "Sem perfil",
            "perfil_grupo": perfil.capitalize() if perfil and not u.is_superuser else "Organizador",
            "eu": u.pk == request.user.pk,
        })
    return render(request, "painel/usuarios.html", {"linhas": linhas, "perfis": ["Organizador", "Caixa", "Vendedor"]})


@acesso("usuarios")
@require_POST
def usuario_salvar(request):
    pk = request.POST.get("id")
    instancia = get_object_or_404(User, pk=pk) if pk else None
    if instancia is not None and instancia.is_superuser:
        messages.error(request, "Superusuários só podem ser alterados pelo /admin/.")
        return redirect("usuarios")
    form = UsuarioForm(request.POST, instancia=instancia)
    if not form.is_valid():
        messages.error(request, "Não foi possível salvar o usuário. " + _erros(form))
        return redirect("usuarios")

    dados = form.cleaned_data
    novo_perfil = dados["perfil"]
    if instancia is not None and instancia.groups.filter(name="Organizador").exists() and novo_perfil != "Organizador":
        if instancia.pk == request.user.pk:
            messages.error(request, "Você não pode tirar o seu próprio perfil de Organizador.")
            return redirect("usuarios")
        if not _outros_organizadores_ativos(instancia.pk):
            messages.error(request, "O sistema precisa ter pelo menos um Organizador ativo.")
            return redirect("usuarios")

    if instancia is None:
        usuario = User.objects.create_user(dados["username"], password=dados["senha"], first_name=dados["first_name"])
    else:
        usuario = instancia
        usuario.first_name = dados["first_name"]
        if dados["senha"]:
            usuario.set_password(dados["senha"])
        usuario.save()
        if dados["senha"] and usuario.pk == request.user.pk:
            update_session_auth_hash(request, usuario)  # não derruba a sessão de quem trocou a própria senha
    grupo, _ = Group.objects.get_or_create(name=novo_perfil)
    usuario.groups.set([grupo])
    messages.success(request, "Usuário salvo.")
    return redirect("usuarios")


@acesso("usuarios")
@require_POST
def usuario_alternar(request, pk):
    """Ativa ou desativa um usuário (desativado não consegue entrar; o histórico de vendas fica)."""
    usuario = get_object_or_404(User, pk=pk)
    if usuario.is_superuser:
        messages.error(request, "Superusuários só podem ser alterados pelo /admin/.")
    elif usuario.pk == request.user.pk:
        messages.error(request, "Você não pode desativar o seu próprio usuário.")
    elif usuario.is_active and perfil_do_usuario(usuario) == "organizador" and not _outros_organizadores_ativos(usuario.pk):
        messages.error(request, "O sistema precisa ter pelo menos um Organizador ativo.")
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        messages.success(request, "Usuário {}.".format("ativado" if usuario.is_active else "desativado"))
    return redirect("usuarios")
