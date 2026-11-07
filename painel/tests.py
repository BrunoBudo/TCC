from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from produtos.models import Produto
from vendas.models import Festa
from vendas.services import registrar_venda

from .sugestoes import gerar_sugestoes


def criar_usuario(login, grupo):
    u = User.objects.create_user(login, password="senha12345")
    u.groups.add(Group.objects.get(name=grupo))
    return u


class BaseTeste(TestCase):
    def setUp(self):
        agora = timezone.now()
        self.festa = Festa.objects.create(nome="Teste", inicio=agora - timedelta(hours=4), fim=agora + timedelta(hours=2))
        self.refri = Produto.objects.create(nome="Refrigerante", categoria="bebida", preco="5.00", quantidade_estoque=10, estoque_minimo=3)
        self.pastel = Produto.objects.create(nome="Pastel", categoria="alimento", preco="6.00", quantidade_estoque=20, estoque_minimo=5)
        self.org = criar_usuario("org", "Organizador")
        self.caixa = criar_usuario("cx", "Caixa")
        self.vend = criar_usuario("vd", "Vendedor")


class PerfisTest(BaseTeste):
    def status(self, nome):
        return self.client.get(reverse(nome)).status_code

    def test_vendedor_so_acessa_vendas(self):
        self.client.force_login(self.vend)
        self.assertEqual(self.status("vendas"), 200)
        for tela in ("dashboard", "produtos", "estoque", "historico", "relatorios", "sugestoes"):
            self.assertEqual(self.status(tela), 403, tela)

    def test_caixa_acessa_vendas_historico_estoque(self):
        self.client.force_login(self.caixa)
        for tela in ("vendas", "historico", "estoque"):
            self.assertEqual(self.status(tela), 200, tela)
        for tela in ("dashboard", "produtos", "relatorios", "sugestoes"):
            self.assertEqual(self.status(tela), 403, tela)
        resp = self.client.post(reverse("estoque_entrada"), {"produto": self.refri.pk, "quantidade": 5})
        self.assertEqual(resp.status_code, 403)

    def test_organizador_acessa_tudo(self):
        self.client.force_login(self.org)
        for tela in ("dashboard", "vendas", "historico", "produtos", "estoque", "relatorios", "sugestoes"):
            self.assertEqual(self.status(tela), 200, tela)
        self.assertEqual(self.client.get(reverse("relatorio_csv")).status_code, 200)

    def test_sem_login_vai_para_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_home_redireciona_por_perfil(self):
        self.client.force_login(self.org)
        self.assertRedirects(self.client.get(reverse("home")), reverse("dashboard"))
        self.client.force_login(self.vend)
        self.assertRedirects(self.client.get(reverse("home")), reverse("vendas"))

    def test_entrada_de_estoque_organizador(self):
        self.client.force_login(self.org)
        self.client.post(reverse("estoque_entrada"), {"produto": self.refri.pk, "quantidade": 15})
        self.refri.refresh_from_db()
        self.assertEqual(self.refri.quantidade_estoque, 25)


class SugestoesTest(BaseTeste):
    def test_esgotou_cedo_gera_sugestao_e_dispensar_remove(self):
        registrar_venda([{"produto_id": self.refri.pk, "quantidade": 10}], operador=self.caixa)
        esgotou = [s for s in gerar_sugestoes(self.festa) if s["chave"].startswith("esgotou-")]
        self.assertEqual(len(esgotou), 1)
        self.assertIn("Refrigerante esgotou", esgotou[0]["titulo"])
        self.client.force_login(self.org)
        self.client.post(reverse("sugestao_dispensar"), {"chave": esgotou[0]["chave"]})
        self.assertFalse([s for s in gerar_sugestoes(self.festa) if s["chave"].startswith("esgotou-")])

    def test_estoque_baixo_gera_sugestao(self):
        self.pastel.quantidade_estoque = 4
        self.pastel.save()
        self.assertTrue([s for s in gerar_sugestoes(self.festa) if s["chave"] == "baixo-{}".format(self.pastel.pk)])
