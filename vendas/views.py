import json
from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from meutcc.permissoes import acesso
from produtos.models import Produto

from .models import Festa, Venda
from .services import EstoqueInsuficienteError, VendaInvalidaError, cancelar_venda, registrar_venda


@acesso("vendas")
def vendas(request):
    return render(request, "vendas/vendas.html", {
        "festa": Festa.atual(), "formas": Venda.FORMAS,
        "produtos": Produto.objects.filter(ativo=True),
    })


@acesso("vendas")
@require_POST
def venda_registrar(request):
    """Recebe o carrinho em JSON (enviado por vendas.js) e chama o service."""
    if Festa.atual() is None:
        return JsonResponse({"ok": False, "erro": "Nenhuma festa ativa. Cadastre uma em /admin/."}, status=400)
    try:
        dados = json.loads(request.body)
        venda = registrar_venda(dados.get("itens", []), operador=request.user, forma_pagamento=dados.get("forma"))
    except (EstoqueInsuficienteError, VendaInvalidaError) as erro:
        return JsonResponse({"ok": False, "erro": str(erro)}, status=400)
    except (ValueError, AttributeError):
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)
    messages.success(request, f"Venda #{venda.pk} registrada: R$ {venda.valor_total:.2f}".replace(".", ","))
    return JsonResponse({"ok": True, "id": venda.pk})


@acesso("historico")
def historico(request):
    festa = Festa.atual()
    qs = Venda.objects.select_related("operador").prefetch_related("itens__produto")
    if festa:
        qs = qs.filter(festa=festa)
    data, forma = request.GET.get("data", ""), request.GET.get("forma", "")
    if data:
        try:
            qs = qs.filter(data_hora__date=date.fromisoformat(data))
        except ValueError:
            pass
    if forma:
        qs = qs.filter(forma_pagamento=forma)
    return render(request, "vendas/historico.html", {
        "vendas": qs[:200], "formas": Venda.FORMAS, "data": data, "forma": forma,
    })


@acesso("venda_cancelar")
@require_POST
def venda_cancelar(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    try:
        cancelar_venda(venda, request.user)
        messages.success(request, f"Venda #{venda.pk} cancelada e itens devolvidos ao estoque.")
    except VendaInvalidaError as erro:
        messages.error(request, str(erro))
    return redirect("historico")
