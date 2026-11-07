from django.urls import path

from . import views

urlpatterns = [
    path("produtos/", views.produtos, name="produtos"),
    path("produtos/salvar/", views.produto_salvar, name="produto_salvar"),
    path("produtos/<int:pk>/excluir/", views.produto_excluir, name="produto_excluir"),
    path("estoque/", views.estoque, name="estoque"),
    path("estoque/entrada/", views.estoque_entrada, name="estoque_entrada"),
]
