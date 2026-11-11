from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views, gestao

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.Login.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("sugestoes/", views.sugestoes, name="sugestoes"),
    path("sugestoes/dispensar/", views.sugestao_dispensar, name="sugestao_dispensar"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/csv/", views.relatorio_csv, name="relatorio_csv"),
    path("festas/", gestao.festas, name="festas"),
    path("festas/salvar/", gestao.festa_salvar, name="festa_salvar"),
    path("festas/<int:pk>/ativar/", gestao.festa_ativar, name="festa_ativar"),
    path("festas/<int:pk>/excluir/", gestao.festa_excluir, name="festa_excluir"),
    path("usuarios/", gestao.usuarios, name="usuarios"),
    path("usuarios/salvar/", gestao.usuario_salvar, name="usuario_salvar"),
    path("usuarios/<int:pk>/alternar/", gestao.usuario_alternar, name="usuario_alternar"),
]
