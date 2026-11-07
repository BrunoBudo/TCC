from django.contrib import admin

from .models import Festa, ItemVenda, Venda


class ItemInline(admin.TabularInline):
    model = ItemVenda
    extra = 0


@admin.register(Festa)
class FestaAdmin(admin.ModelAdmin):
    list_display = ("nome", "inicio", "fim", "ativa")


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "data_hora", "operador", "forma_pagamento", "valor_total", "cancelada")
    inlines = [ItemInline]
