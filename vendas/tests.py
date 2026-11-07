import json
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from produtos.models import Produto

from .models import Festa, Venda
from .services import EstoqueInsuficienteError, VendaInvalidaError, cancelar_venda, registrar_venda


def criar_usuario(login, grupo):
    u = User.objects.create_user(login, password="senha12345")
    u.groups.add(Group.objects.get(name=grupo))
    return u


class VendaTest(TestCase):
    def setUp(self):
        agora = timezone.now()
        self.festa = Festa.objects.create(nome="Teste", inicio=agora - timedelta(hours=4), fim=agora + timedelta(hours=2))
        self.refri = Produto.objects.create(nome="Refrigerante", categoria="bebida", preco="5.00", quantidade_estoque=10)
        self.pastel = Produto.objects.create(nome="Pastel", categoria="alimento", preco="6.00", quantidade_estoque=20)
        self.org = criar_usuario("org", "Organizador")
        self.caixa = criar_usuario("cx", "Caixa")
        self.vend = criar_usuario("vd", "Vendedor")

    def test_service_baixa_estoque_e_calcula_total(self):
        venda = registrar_venda(
            [{"produto_id": self.refri.pk, "quantidade": 2}, {"produto_id": self.pastel.pk, "quantidade": 3}],
            operador=self.caixa, forma_pagamento="pix",
        )
        self.refri.refresh_from_db()
        self.pastel.refresh_from_db()
        self.assertEqual((self.refri.quantidade_estoque, self.pastel.quantidade_estoque), (8, 17))
        self.assertEqual(venda.valor_total, 28)
        self.assertEqual(venda.festa, self.festa)

    def test_estoque_insuficiente_desfaz_tudo(self):
        with self.assertRaises(EstoqueInsuficienteError):
            registrar_venda([{"produto_id": self.pastel.pk, "quantidade": 1}, {"produto_id": self.refri.pk, "quantidade": 99}])
        self.pastel.refresh_from_db()
        self.assertEqual(self.pastel.quantidade_estoque, 20)
        self.assertEqual(Venda.objects.count(), 0)

    def test_dados_invalidos(self):
        for itens in ([], [{"produto_id": self.pastel.pk, "quantidade": 0}], [{"produto_id": 9999, "quantidade": 1}]):
            with self.assertRaises(VendaInvalidaError):
                registrar_venda(itens)

    def test_esgotar_marca_horario(self):
        registrar_venda([{"produto_id": self.refri.pk, "quantidade": 10}])
        self.refri.refresh_from_db()
        self.assertIsNotNone(self.refri.esgotou_em)

    def test_view_registrar_venda(self):
        self.client.force_login(self.vend)
        corpo = {"forma": "pix", "itens": [{"produto_id": self.refri.pk, "quantidade": 2}]}
        resp = self.client.post(reverse("venda_registrar"), json.dumps(corpo), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.refri.refresh_from_db()
        self.assertEqual(self.refri.quantidade_estoque, 8)

    def test_view_estoque_insuficiente_retorna_400(self):
        self.client.force_login(self.vend)
        corpo = {"forma": "pix", "itens": [{"produto_id": self.refri.pk, "quantidade": 99}]}
        resp = self.client.post(reverse("venda_registrar"), json.dumps(corpo), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Venda.objects.count(), 0)

    def test_cancelar_devolve_estoque_so_organizador(self):
        venda = registrar_venda([{"produto_id": self.refri.pk, "quantidade": 4}], operador=self.caixa)
        self.client.force_login(self.caixa)
        self.assertEqual(self.client.post(reverse("venda_cancelar", args=[venda.pk])).status_code, 403)
        self.client.force_login(self.org)
        self.client.post(reverse("venda_cancelar", args=[venda.pk]))
        self.refri.refresh_from_db()
        venda.refresh_from_db()
        self.assertEqual(self.refri.quantidade_estoque, 10)
        self.assertTrue(venda.cancelada)
        with self.assertRaises(VendaInvalidaError):
            cancelar_venda(venda, self.org)
