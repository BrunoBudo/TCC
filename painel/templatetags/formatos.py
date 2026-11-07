from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def brl(valor):
    """Formata como moeda brasileira: 1264 -> R$ 1.264,00"""
    try:
        numero = Decimal(valor or 0)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    texto = f"{numero:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
