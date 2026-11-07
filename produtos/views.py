from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from meutcc.permissoes import acesso

from .forms import ProdutoForm
from .models import MovimentacaoEstoque, Produto
from .services import entrada_estoque


@acesso("produtos")
def produtos(request):
    q, cat = request.GET.get("q", "").strip(), request.GET.get("categoria", "")
    qs = Produto.objects.filter(ativo=True)
    if q:
        qs = qs.filter(nome__icontains=q)
    if cat:
        qs = qs.filter(categoria=cat)
    return render(request, "produtos/produtos.html", {
        "produtos": qs, "categorias": Produto.CATEGORIA_CHOICES, "q": q, "cat": cat,
    })


@acesso("produtos")
@require_POST
def produto_salvar(request):
    pk = request.POST.get("id")
    instancia = get_object_or_404(Produto, pk=pk) if pk else None
    form = ProdutoForm(request.POST, instance=instancia)
    if not form.is_valid():
        messages.error(request, "Não foi possível salvar: confira os campos do produto.")
        return redirect("produtos")
    produto = form.save(commit=False)
    if instancia is None:
        produto.quantidade_estoque = form.cleaned_data.get("estoque_inicial") or 0
    produto.save()
    if instancia is None and produto.quantidade_estoque:
        MovimentacaoEstoque.objects.create(
            produto=produto, tipo="entrada", quantidade=produto.quantidade_estoque,
            operador=request.user, motivo="Estoque inicial",
        )
    messages.success(request, "Produto salvo.")
    return redirect("produtos")


@acesso("produtos")
@require_POST
def produto_excluir(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if produto.itens_venda.exists():
        produto.ativo = False  # já tem vendas: só esconde, para não quebrar o histórico
        produto.save(update_fields=["ativo"])
    else:
        produto.delete()
    messages.success(request, "Produto excluído.")
    return redirect("produtos")


@acesso("estoque")
def estoque(request):
    filtro = request.GET.get("status", "")
    lista = [p for p in Produto.objects.filter(ativo=True) if not filtro or p.status == filtro]
    return render(request, "produtos/estoque.html", {
        "produtos": lista, "filtro": filtro, "todos": Produto.objects.filter(ativo=True),
    })


@acesso("estoque_editar")
@require_POST
def estoque_entrada(request):
    produto = get_object_or_404(Produto, pk=request.POST.get("produto"), ativo=True)
    try:
        entrada_estoque(produto, int(request.POST.get("quantidade") or 0), request.user, request.POST.get("motivo", ""))
        messages.success(request, f"Entrada registrada para {produto.nome}.")
    except ValueError as erro:
        messages.error(request, str(erro))
    return redirect("estoque")
