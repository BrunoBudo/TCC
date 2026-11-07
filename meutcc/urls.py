"""
URL configuration for meutcc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

def inicio(request):
    if not request.user.is_authenticated:
        return redirect('login') # Substitua 'login' pelo nome da sua rota de login
    return redirect('dashboard') # Redireciona quem já está logado


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("painel.urls")),
    path("", include("produtos.urls")),
    path("", include("vendas.urls")),
]

