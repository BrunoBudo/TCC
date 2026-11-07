"""Cria os usuários de cada perfil e (opcionalmente) dados de exemplo.

Uso:
  python manage.py seed                  -> só cria/atualiza os 3 usuários e os grupos
  python manage.py seed --demo           -> também cria festa, produtos e vendas de exemplo
                                            (só se NÃO existir nenhum produto)
  python manage.py seed --demo --limpar  -> APAGA produtos, vendas e festas e recria o exemplo
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from painel.models import SugestaoDispensada
from produtos.models import MovimentacaoEstoque, Produto
from vendas.models import Festa, ItemVenda, Venda

USUARIOS = [
    ("organizador", "Organizador", "festa123"),
    ("caixa", "Caixa", "festa123"),
    ("vendedor", "Vendedor", "festa123"),
]

# nome, categoria, preço, estoque inicial, mínimo, [(unidades, minuto_inicial, minuto_final)]
# os minutos contam a partir do início da festa (a festa de exemplo está no minuto 240 de 330)
PLANO = [
    ("Pastel", "alimento", "6.00", 120, 20, [(100, 0, 238)]),
    ("Pamonha", "alimento", "8.00", 80, 15, [(40, 0, 238)]),
    ("Cachorro-quente", "alimento", "7.00", 40, 15, [(3, 0, 110), (28, 125, 238)]),
    ("Refrigerante", "bebida", "5.00", 60, 20, [(60, 60, 138)]),
    ("Suco natural", "bebida", "6.00", 50, 10, [(30, 0, 238)]),
    ("Bolo de milho", "outro", "5.00", 40, 10, [(8, 0, 238)]),
    ("Canjica", "outro", "6.00", 40, 10, [(20, 0, 238)]),
    ("Pipoca", "outro", "4.00", 30, 10, [(23, 0, 238)]),
]


class Command(BaseCommand):
    help = "Cria usuários de cada perfil e dados de exemplo"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="cria festa, produtos e vendas de exemplo")
        parser.add_argument("--limpar", action="store_true", help="com --demo: apaga os dados atuais antes")

    def handle(self, *args, **opcoes):
        for nome in ("Organizador", "Caixa", "Vendedor"):
            Group.objects.get_or_create(name=nome)
        usuarios = {}
        for login, grupo, senha in USUARIOS:
            usuario, criado = User.objects.get_or_create(username=login)
            if criado:
                usuario.set_password(senha)
                usuario.save()
            usuario.groups.set([Group.objects.get(name=grupo)])
            usuarios[login] = usuario
        self.stdout.write(self.style.SUCCESS("Usuários prontos (senha inicial: festa123)."))
        for login, grupo, _ in USUARIOS:
            self.stdout.write("  {}  ->  perfil {}".format(login, grupo))
        if not opcoes["demo"]:
            return

        if opcoes["limpar"]:
            for modelo in (SugestaoDispensada, ItemVenda, MovimentacaoEstoque, Venda, Produto, Festa):
                modelo.objects.all().delete()
        if Produto.objects.exists():
            self.stdout.write("Já existem produtos: nada foi criado. Use --demo --limpar para recriar (apaga tudo).")
            return

        rng = random.Random(42)
        agora = timezone.now()
        inicio = agora - timedelta(minutes=240)
        festa = Festa.objects.create(nome="Festa de Exemplo", inicio=inicio, fim=inicio + timedelta(minutes=330))

        produtos, linhas = {}, []
        for nome, cat, preco, estoque_ini, minimo, janelas in PLANO:
            p = Produto.objects.create(nome=nome, categoria=cat, preco=Decimal(preco),
                                       quantidade_estoque=estoque_ini, estoque_minimo=minimo)
            produtos[nome] = p
            MovimentacaoEstoque.objects.create(produto=p, tipo="entrada", quantidade=estoque_ini,
                                               operador=usuarios["organizador"], motivo="Estoque inicial",
                                               criada_em=inicio - timedelta(minutes=30))
            for unidades, m1, m2 in janelas:
                restante = unidades
                while restante > 0:
                    q = min(restante, rng.randint(1, 3))
                    linhas.append((rng.uniform(m1, m2), p, q))
                    restante -= q
        linhas.sort(key=lambda x: x[0])

        operadores = [usuarios["caixa"], usuarios["vendedor"]]
        i = 0
        while i < len(linhas):
            grupo = linhas[i:i + rng.randint(1, 3)]
            i += len(grupo)
            momento = inicio + timedelta(minutes=grupo[0][0])
            venda = Venda.objects.create(
                festa=festa, operador=rng.choice(operadores),
                forma_pagamento=rng.choices(["pix", "dinheiro", "cartao"], [50, 30, 20])[0],
            )
            total = Decimal("0")
            for _, p, q in grupo:
                ItemVenda.objects.create(venda=venda, produto=p, quantidade=q, preco_unitario=p.preco)
                MovimentacaoEstoque.objects.create(produto=p, tipo="saida", quantidade=-q,
                                                   motivo="Venda #{}".format(venda.pk), criada_em=momento)
                p.quantidade_estoque -= q
                total += p.preco * q
                if p.quantidade_estoque == 0:
                    p.esgotou_em = momento
            # data_hora usa auto_now_add, então ajustamos o horário com update()
            Venda.objects.filter(pk=venda.pk).update(valor_total=total, data_hora=momento)
        for p in produtos.values():
            p.save(update_fields=["quantidade_estoque", "esgotou_em"])
        self.stdout.write(self.style.SUCCESS("Dados de exemplo criados (festa em andamento)."))
