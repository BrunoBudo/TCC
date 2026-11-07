from django.db import transaction
from django.utils import timezone

from produtos.models import MovimentacaoEstoque, Produto
from .models import Festa, ItemVenda, Venda


class EstoqueInsuficienteError(Exception):
    """Lançado quando não há estoque suficiente para concluir a venda."""
    pass


class VendaInvalidaError(Exception):
    """Lançado quando os dados da venda são inválidos (produto inexistente, quantidade zero...)."""
    pass


@transaction.atomic
def registrar_venda(itens, operador=None, forma_pagamento="dinheiro", festa=None):
    """
    Registra uma venda e dá baixa no estoque dos produtos.

    itens: lista de dicionários no formato
        [{"produto_id": 1, "quantidade": 2}, ...]
    operador: usuário (opcional) que realizou a venda
    forma_pagamento: "dinheiro", "pix" ou "cartao"
    festa: festa da venda (se não vier, usa a festa ativa)

    Retorna a Venda criada.
    Lança EstoqueInsuficienteError se algum produto não tiver estoque suficiente
    e VendaInvalidaError se os dados forem inválidos.
    """
    if forma_pagamento not in dict(Venda.FORMAS):
        raise VendaInvalidaError("Forma de pagamento inválida.")

    quantidades = {}  # junta linhas repetidas do mesmo produto
    for item in itens:
        try:
            produto_id, quantidade = int(item["produto_id"]), int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            raise VendaInvalidaError("Dados do carrinho inválidos.")
        if quantidade <= 0:
            raise VendaInvalidaError("Quantidade inválida.")
        quantidades[produto_id] = quantidades.get(produto_id, 0) + quantidade
    if not quantidades:
        raise VendaInvalidaError("Adicione ao menos um produto.")

    venda = Venda.objects.create(
        operador=operador, forma_pagamento=forma_pagamento, festa=festa or Festa.atual()
    )
    agora = timezone.now()

    for produto_id, quantidade in quantidades.items():
        try:
            produto = Produto.objects.select_for_update().get(pk=produto_id, ativo=True)
        except Produto.DoesNotExist:
            raise VendaInvalidaError("Produto não encontrado.")

        if produto.quantidade_estoque < quantidade:
            raise EstoqueInsuficienteError(
                f"Estoque insuficiente para '{produto.nome}'. "
                f"Disponível: {produto.quantidade_estoque}, solicitado: {quantidade}"
            )

        ItemVenda.objects.create(
            venda=venda,
            produto=produto,
            quantidade=quantidade,
            preco_unitario=produto.preco,
        )

        produto.quantidade_estoque -= quantidade
        if produto.quantidade_estoque == 0:
            produto.esgotou_em = agora  # usado pelas sugestões ("esgotou cedo")
        produto.save(update_fields=["quantidade_estoque", "esgotou_em"])

        MovimentacaoEstoque.objects.create(
            produto=produto, tipo="saida", quantidade=-quantidade, operador=operador,
            motivo=f"Venda #{venda.pk}",
        )

    venda.calcular_total()
    return venda


@transaction.atomic
def cancelar_venda(venda, operador=None):
    """Marca a venda como cancelada e devolve os itens ao estoque."""
    venda = Venda.objects.select_for_update().get(pk=venda.pk)
    if venda.cancelada:
        raise VendaInvalidaError("Esta venda já foi cancelada.")
    for item in venda.itens.select_related("produto"):
        produto = Produto.objects.select_for_update().get(pk=item.produto.pk)
        produto.quantidade_estoque += item.quantidade
        produto.esgotou_em = None
        produto.save(update_fields=["quantidade_estoque", "esgotou_em"])
        MovimentacaoEstoque.objects.create(
            produto=produto, tipo="estorno", quantidade=item.quantidade, operador=operador,
            motivo=f"Cancelamento da venda #{venda.pk}",
        )
    venda.cancelada = True
    venda.save(update_fields=["cancelada"])
    return venda
