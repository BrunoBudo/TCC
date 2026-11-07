from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.Login.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("sugestoes/", views.sugestoes, name="sugestoes"),
    path("sugestoes/dispensar/", views.sugestao_dispensar, name="sugestao_dispensar"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/csv/", views.relatorio_csv, name="relatorio_csv"),
]
