from django.contrib import admin
from .models import Venda, ItemVenda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "data_hora", "operador", "valor_total")
    inlines = [ItemVendaInline]
