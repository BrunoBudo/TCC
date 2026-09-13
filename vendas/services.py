from django.db import transaction
from produtos.models import Produto
from .models import Venda, ItemVenda


class EstoqueInsuficienteError(Exception):
    """Lançado quando não há estoque suficiente para concluir a venda."""
    pass


@transaction.atomic
def registrar_venda(itens, operador=None):
    """
    Registra uma venda e dá baixa no estoque dos produtos.

    itens: lista de dicionários no formato
        [{"produto_id": 1, "quantidade": 2}, ...]
    operador: usuário (opcional) que realizou a venda

    Retorna a Venda criada.
    Lança EstoqueInsuficienteError se algum produto não tiver estoque suficiente.
    """
    venda = Venda.objects.create(operador=operador)

    for item in itens:
        produto = Produto.objects.select_for_update().get(pk=item["produto_id"])
        quantidade = item["quantidade"]

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
        produto.save(update_fields=["quantidade_estoque"])

    venda.calcular_total()
    return venda