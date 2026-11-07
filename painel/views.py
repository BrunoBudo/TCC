import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from meutcc.permissoes import acesso, perfil_do_usuario
from produtos.models import MovimentacaoEstoque, Produto
from vendas.models import Festa, ItemVenda, Venda

from .models import SugestaoDispensada
from .sugestoes import gerar_sugestoes, recomendacoes


class Login(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True


def home(request):
    """Depois do login, cada perfil vai para a sua tela inicial."""
    if not request.user.is_authenticated:
        return redirect("login")
    perfil = perfil_do_usuario(request.user)
    if perfil == "organizador":
        return redirect("dashboard")
    if perfil:
        return redirect("vendas")
    raise PermissionDenied


def _barras(linhas):
    maior = max([v for _, v in linhas], default=0) or 1
    return [{"rotulo": r, "valor": v, "altura": max(6, int(v / maior * 130))} for r, v in linhas]


@acesso("dashboard")
def dashboard(request):
    festa = Festa.atual()
    vendas = Venda.objects.filter(festa=festa, cancelada=False) if festa else Venda.objects.none()
    agg = vendas.aggregate(qtd=Count("id"), total=Sum("valor_total"))
    qtd, total = agg["qtd"] or 0, agg["total"] or Decimal("0")
    por_hora = vendas.annotate(h=TruncHour("data_hora")).values("h").annotate(n=Count("id")).order_by("h")
    barras = _barras([(timezone.localtime(r["h"]).strftime("%Hh"), r["n"]) for r in por_hora])
    top = list(
        ItemVenda.objects.filter(venda__in=vendas)
        .values("produto__nome").annotate(q=Sum("quantidade")).order_by("-q")[:5]
    )
    maior = top[0]["q"] if top else 1
    for t in top:
        t["nome"], t["pct"] = t["produto__nome"], int(t["q"] / maior * 100)
    alertas = [p for p in Produto.objects.filter(ativo=True) if p.status != "normal"]
    return render(request, "painel/dashboard.html", {
        "festa": festa, "qtd": qtd, "total": total,
        "ticket": total / qtd if qtd else Decimal("0"),
        "alertas": alertas, "barras": barras, "top": top,
    })


@acesso("sugestoes")
def sugestoes(request):
    festa = Festa.atual()
    return render(request, "painel/sugestoes.html", {
        "festa": festa, "sugestoes": gerar_sugestoes(festa), "recomendacoes": recomendacoes(festa),
    })


@acesso("sugestoes")
@require_POST
def sugestao_dispensar(request):
    festa = Festa.atual()
    chave = request.POST.get("chave", "")
    if festa and chave:
        SugestaoDispensada.objects.get_or_create(festa=festa, chave=chave)
    return redirect("sugestoes")


def _vendas_do_periodo(periodo):
    qs = Venda.objects.filter(cancelada=False)
    if periodo == "hoje":
        return "hoje", qs.filter(data_hora__date=timezone.localdate())
    if periodo == "7dias":
        return "7dias", qs.filter(data_hora__gte=timezone.now() - timedelta(days=7))
    festa = Festa.atual()
    return "festa", (qs.filter(festa=festa) if festa else qs.none())


@acesso("relatorios")
def relatorios(request):
    periodo, vendas_qs = _vendas_do_periodo(request.GET.get("periodo", "festa"))
    por_forma = {f: Decimal("0") for f, _ in Venda.FORMAS}
    for r in vendas_qs.values("forma_pagamento").annotate(t=Sum("valor_total")):
        por_forma[r["forma_pagamento"]] = r["t"]
    por_dia = vendas_qs.annotate(d=TruncDate("data_hora")).values("d").annotate(t=Sum("valor_total")).order_by("d")
    barras = _barras([(r["d"].strftime("%d/%m"), r["t"]) for r in por_dia])
    return render(request, "painel/relatorios.html", {
        "periodo": periodo,
        "total": vendas_qs.aggregate(t=Sum("valor_total"))["t"] or Decimal("0"),
        "por_forma": [(rotulo, por_forma[v]) for v, rotulo in Venda.FORMAS],
        "barras": barras,
        "movimentacoes": MovimentacaoEstoque.objects.select_related("produto")[:10],
    })


@acesso("relatorios")
def relatorio_csv(request):
    _, vendas_qs = _vendas_do_periodo(request.GET.get("periodo", "festa"))
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="vendas.csv"'
    resposta.write("\ufeff")  # BOM: o Excel abre com acentos corretos
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow(["Nº", "Data", "Pagamento", "Operador", "Itens", "Total (R$)"])
    for v in vendas_qs.select_related("operador").prefetch_related("itens__produto").order_by("data_hora"):
        itens = ", ".join("{}x {}".format(i.quantidade, i.produto.nome) for i in v.itens.all())
        escritor.writerow([
            v.pk, timezone.localtime(v.data_hora).strftime("%d/%m/%Y %H:%M"), v.get_forma_pagamento_display(),
            v.operador.username if v.operador else "", itens, str(v.valor_total).replace(".", ","),
        ])
    return resposta
