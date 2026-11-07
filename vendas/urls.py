from django.urls import path

from . import views

urlpatterns = [
    path("vendas/", views.vendas, name="vendas"),
    path("vendas/registrar/", views.venda_registrar, name="venda_registrar"),
    path("historico/", views.historico, name="historico"),
    path("historico/<int:pk>/cancelar/", views.venda_cancelar, name="venda_cancelar"),
]
