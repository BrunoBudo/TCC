"""Módulo de sugestões baseado em REGRAS (não usa IA).

Cada regra olha os números da festa ativa (vendas, estoque, horário) e, se a
condição for verdadeira, gera uma sugestão para o organizador.
"""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncHour
from django.utils import timezone

from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from .models import SugestaoDispensada

LIMITE_ENCALHE = 0.30   # vendeu menos de 30% do que tinha = encalhou
LIMITE_ESGOTOU_CEDO = 0.85  # esgotou antes de 85% da festa = esgotou cedo
JANELA_RITMO_HORAS = 2  # o ritmo de vendas é calculado com as últimas 2 horas

ORDEM = {"out": 0, "low": 1, "ok": 2}


def _extra(fracao):
    """Quanto comprar a mais: quanto mais cedo esgotou, maior o acréscimo (múltiplos de 5%)."""
    return max(10, int(round((1 - fracao) * 50 / 5.0)) * 5)


def _hora(dt):
    return timezone.localtime(dt).strftime("%Hh%M")


def _duracao(horas):
    minutos = int(horas * 60)
    return f"{minutos // 60}h{minutos % 60:02d}" if minutos >= 60 else f"{minutos} minutos"


def _vendidos(festa, desde=None):
    qs = ItemVenda.objects.filter(venda__festa=festa, venda__cancelada=False)
    if desde:
        qs = qs.filter(venda__data_hora__gte=desde)
    return {r["produto"]: r["q"] for r in qs.values("produto").annotate(q=Sum("quantidade"))}


def _sug(chave, tipo, rotulo, titulo, texto):
    return {"chave": chave, "tipo": tipo, "rotulo": rotulo, "titulo": titulo, "texto": texto}


def gerar_sugestoes(festa, agora=None):
    if festa is None:
        return []
    agora = agora or timezone.now()
    fracao = festa.progresso(agora)
    em_andamento = festa.inicio <= agora <= festa.fim
    horas_decorridas = max((agora - festa.inicio).total_seconds() / 3600, 0.25)
    janela = min(JANELA_RITMO_HORAS, horas_decorridas)
    horas_restantes = max((festa.fim - agora).total_seconds() / 3600, 0)

    vendidos = _vendidos(festa)
    recentes = _vendidos(festa, desde=agora - timedelta(hours=JANELA_RITMO_HORAS))
    sugestoes = []

    for p in Produto.objects.filter(ativo=True):
        vend = vendidos.get(p.pk, 0)
        # Regra 1: esgotou cedo
        if p.quantidade_estoque == 0 and p.esgotou_em and festa.inicio <= p.esgotou_em <= festa.fim:
            f = festa.progresso(p.esgotou_em)
            if f < LIMITE_ESGOTOU_CEDO:
                chave = f"esgotou-{p.pk}-{int(p.esgotou_em.timestamp())}"
                sugestoes.append(_sug(
                    chave, "out", "Urgente", f"{p.nome} esgotou às {_hora(p.esgotou_em)}",
                    f"Sugestão: comprar cerca de {_extra(f)}% a mais na próxima festa.",
                ))
            continue
        # Regra 2: vai acabar antes do fim da festa (pelo ritmo das últimas horas)
        taxa = recentes.get(p.pk, 0) / janela
        if p.quantidade_estoque > 0 and em_andamento and taxa > 0:
            duracao = p.quantidade_estoque / taxa
            if duracao < horas_restantes:
                sugestoes.append(_sug(
                    f"acabando-{p.pk}", "low", "Atenção",
                    f"{p.nome} deve acabar em cerca de {_duracao(duracao)}",
                    f"Vende em média {round(taxa)} por hora e restam {p.quantidade_estoque}. Considere repor antes do pico.",
                ))
                continue
        # Regra 3: estoque abaixo do mínimo
        if 0 < p.quantidade_estoque <= p.estoque_minimo:
            sugestoes.append(_sug(
                f"baixo-{p.pk}", "low", "Atenção", f"{p.nome} com estoque baixo",
                f"Restam {p.quantidade_estoque} unidades, abaixo do mínimo de {p.estoque_minimo}.",
            ))
            continue
        # Regra 4: encalhou (só faz sentido perto do fim da festa)
        total = vend + p.quantidade_estoque
        if fracao >= 0.7 and p.quantidade_estoque > 0 and total > 0 and vend / total < LIMITE_ENCALHE:
            sugestoes.append(_sug(
                f"encalhou-{p.pk}", "ok", "Dica", f"{p.nome} vendeu pouco",
                f"Saiu só {round(vend / total * 100)}% do estoque. Considere uma promoção agora "
                "ou comprar menos na próxima festa.",
            ))

    # Regra 5: produto mais vendido
    if vendidos:
        top_id = max(vendidos, key=vendidos.get)
        top = Produto.objects.filter(pk=top_id).first()
        if top:
            sugestoes.append(_sug(
                "mais-vendido", "ok", "Dica", f"{top.nome} é o mais vendido ({vendidos[top_id]} unidades)",
                "Priorize a reposição desse produto.",
            ))

    # Regra 6: horário de pico
    pico = (
        Venda.objects.filter(festa=festa, cancelada=False)
        .annotate(h=TruncHour("data_hora"))
        .values("h").annotate(n=Count("id")).order_by("-n", "h").first()
    )
    if pico and pico["n"] >= 5:
        h = timezone.localtime(pico["h"])
        sugestoes.append(_sug(
            "pico", "ok", "Dica", f"Horário de pico: {h.hour}h às {(h.hour + 1) % 24}h",
            "Reforce a equipe no caixa e nas barracas nesse período.",
        ))

    dispensadas = set(SugestaoDispensada.objects.filter(festa=festa).values_list("chave", flat=True))
    sugestoes = [s for s in sugestoes if s["chave"] not in dispensadas]
    sugestoes.sort(key=lambda s: ORDEM[s["tipo"]])
    return sugestoes


def recomendacoes(festa):
    """Tabela 'o que aconteceu / o que fazer na próxima festa'."""
    if festa is None:
        return []
    fracao = festa.progresso()
    vendidos = _vendidos(festa)
    top_id = max(vendidos, key=vendidos.get) if vendidos else None
    linhas = []
    for p in Produto.objects.filter(ativo=True):
        vend = vendidos.get(p.pk, 0)
        total = vend + p.quantidade_estoque
        if p.quantidade_estoque == 0 and p.esgotou_em and festa.inicio <= p.esgotou_em <= festa.fim:
            f = festa.progresso(p.esgotou_em)
            if f < LIMITE_ESGOTOU_CEDO:
                linhas.append({"produto": p.nome, "aconteceu": f"Esgotou às {_hora(p.esgotou_em)}",
                               "sugestao": f"Comprar cerca de {_extra(f)}% a mais"})
            else:
                linhas.append({"produto": p.nome, "aconteceu": "Esgotou perto do fim da festa",
                               "sugestao": "Manter a quantidade"})
        elif fracao >= 0.7 and total > 0 and vend / total < LIMITE_ENCALHE:
            linhas.append({"produto": p.nome, "aconteceu": f"Vendeu só {round(vend / total * 100)}% do estoque",
                           "sugestao": "Reduzir a quantidade ou fazer promoção"})
        elif p.pk == top_id:
            linhas.append({"produto": p.nome, "aconteceu": f"Mais vendido da festa ({vend} unidades)",
                           "sugestao": "Manter a quantidade e priorizar a reposição"})
    return linhas
