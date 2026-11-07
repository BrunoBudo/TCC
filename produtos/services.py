from django.db import transaction

from .models import MovimentacaoEstoque, Produto


def entrada_estoque(produto, quantidade, operador=None, motivo=""):
    """Soma 'quantidade' ao estoque do produto e registra a movimentação."""
    if quantidade <= 0:
        raise ValueError("Informe uma quantidade maior que zero.")
    with transaction.atomic():
        produto = Produto.objects.select_for_update().get(pk=produto.pk)
        produto.quantidade_estoque += quantidade
        produto.esgotou_em = None
        produto.save(update_fields=["quantidade_estoque", "esgotou_em"])
        MovimentacaoEstoque.objects.create(
            produto=produto, tipo="entrada", quantidade=quantidade, operador=operador,
            motivo=motivo or "Entrada de mercadoria",
        )
    return produto
