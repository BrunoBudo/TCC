from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from meutcc.permissoes import perfil_do_usuario
from vendas.models import Festa


def criar_usuario(login, grupo):
    u = User.objects.create_user(login, password="SenhaForte#2026")
    u.groups.add(Group.objects.get(name=grupo))
    return u


class BaseGestao(TestCase):
    def setUp(self):
        self.org = criar_usuario("org", "Organizador")
        self.caixa = criar_usuario("cx", "Caixa")
        self.vend = criar_usuario("vd", "Vendedor")


class AcessoTest(BaseGestao):
    def test_so_organizador_acessa(self):
        for nome in ("festas", "usuarios"):
            self.client.force_login(self.org)
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)
            for outro in (self.caixa, self.vend):
                self.client.force_login(outro)
                self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)

    def test_acoes_de_post_bloqueadas_para_outros_perfis(self):
        self.client.force_login(self.caixa)
        resp = self.client.post(reverse("usuario_salvar"), {"username": "x", "perfil": "Caixa", "senha": "SenhaForte#2026"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(username="x").exists())
        resp = self.client.post(reverse("festa_salvar"), {"nome": "X", "inicio": "2026-11-10T10:00", "fim": "2026-11-10T12:00"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Festa.objects.count(), 0)


class FestaTest(BaseGestao):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.org)

    def dados(self, **extra):
        base = {"nome": "Festa Junina", "inicio": "2026-11-10T18:00", "fim": "2026-11-10T23:00", "ativa": "on"}
        base.update(extra)
        return base

    def test_criar_festa_ativa_desativa_as_outras(self):
        self.client.post(reverse("festa_salvar"), self.dados(nome="Primeira"))
        self.client.post(reverse("festa_salvar"), self.dados(nome="Segunda"))
        self.assertEqual(Festa.objects.count(), 2)
        self.assertEqual(Festa.atual().nome, "Segunda")
        self.assertEqual(Festa.objects.filter(ativa=True).count(), 1)

    def test_horario_vale_no_fuso_de_sao_paulo(self):
        self.client.post(reverse("festa_salvar"), self.dados())
        festa = Festa.objects.get()
        self.assertEqual(timezone.localtime(festa.inicio).strftime("%H:%M"), "18:00")

    def test_fim_antes_do_inicio_nao_salva(self):
        self.client.post(reverse("festa_salvar"), self.dados(fim="2026-11-10T17:00"))
        self.assertEqual(Festa.objects.count(), 0)

    def test_editar_ativar_e_excluir(self):
        self.client.post(reverse("festa_salvar"), self.dados(nome="A"))
        self.client.post(reverse("festa_salvar"), self.dados(nome="B"))
        a = Festa.objects.get(nome="A")
        self.client.post(reverse("festa_ativar", args=[a.pk]))
        self.assertEqual(Festa.atual(), a)
        self.client.post(reverse("festa_salvar"), self.dados(id=a.pk, nome="A renomeada"))
        a.refresh_from_db()
        self.assertEqual(a.nome, "A renomeada")
        self.client.post(reverse("festa_excluir", args=[Festa.objects.get(nome="B").pk]))
        self.assertEqual(Festa.objects.count(), 1)

    def test_nao_exclui_festa_com_vendas(self):
        from produtos.models import Produto
        from vendas.services import registrar_venda

        self.client.post(reverse("festa_salvar"), self.dados())
        festa = Festa.objects.get()
        p = Produto.objects.create(nome="Pastel", preco="6.00", quantidade_estoque=5)
        registrar_venda([{"produto_id": p.pk, "quantidade": 1}], operador=self.org)
        self.client.post(reverse("festa_excluir", args=[festa.pk]))
        self.assertEqual(Festa.objects.count(), 1)


class UsuarioTest(BaseGestao):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.org)

    def test_criar_usuario_com_perfil_e_logar(self):
        self.client.post(reverse("usuario_salvar"), {
            "username": "maria", "first_name": "Maria", "perfil": "Caixa", "senha": "SenhaForte#2026"})
        maria = User.objects.get(username="maria")
        self.assertEqual(perfil_do_usuario(maria), "caixa")
        self.client.logout()
        self.assertTrue(self.client.login(username="maria", password="SenhaForte#2026"))
        self.assertRedirects(self.client.get(reverse("home")), reverse("vendas"))

    def test_senha_fraca_e_nome_repetido_sao_recusados(self):
        self.client.post(reverse("usuario_salvar"), {"username": "joao", "perfil": "Vendedor", "senha": "123"})
        self.assertFalse(User.objects.filter(username="joao").exists())
        self.client.post(reverse("usuario_salvar"), {"username": "CX", "perfil": "Vendedor", "senha": "SenhaForte#2026"})
        self.assertEqual(User.objects.filter(username__iexact="cx").count(), 1)

    def test_editar_perfil_e_trocar_senha(self):
        self.client.post(reverse("usuario_salvar"), {
            "id": self.vend.pk, "first_name": "Zé", "perfil": "Caixa", "senha": "OutraSenha#2026"})
        self.vend.refresh_from_db()
        self.assertEqual(perfil_do_usuario(self.vend), "caixa")
        self.assertEqual(self.vend.first_name, "Zé")
        self.assertTrue(self.vend.check_password("OutraSenha#2026"))

    def test_editar_sem_senha_mantem_a_senha(self):
        self.client.post(reverse("usuario_salvar"), {"id": self.vend.pk, "perfil": "Vendedor", "senha": ""})
        self.vend.refresh_from_db()
        self.assertTrue(self.vend.check_password("SenhaForte#2026"))

    def test_desativar_impede_login(self):
        self.client.post(reverse("usuario_alternar", args=[self.vend.pk]))
        self.vend.refresh_from_db()
        self.assertFalse(self.vend.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username="vd", password="SenhaForte#2026"))

    def test_protecoes_do_organizador(self):
        # não pode desativar a si mesmo nem tirar o próprio perfil
        self.client.post(reverse("usuario_alternar", args=[self.org.pk]))
        self.org.refresh_from_db()
        self.assertTrue(self.org.is_active)
        self.client.post(reverse("usuario_salvar"), {"id": self.org.pk, "perfil": "Caixa"})
        self.assertEqual(perfil_do_usuario(self.org), "organizador")
        # não pode deixar o sistema sem organizador ativo
        segundo = criar_usuario("org2", "Organizador")
        self.client.force_login(segundo)
        self.client.post(reverse("usuario_alternar", args=[self.org.pk]))  # ainda sobra o "segundo"
        self.org.refresh_from_db()
        self.assertFalse(self.org.is_active)
        self.client.post(reverse("usuario_salvar"), {"id": segundo.pk, "perfil": "Vendedor"})
        self.assertEqual(perfil_do_usuario(segundo), "organizador")

    def test_superusuario_nao_e_alterado_por_aqui(self):
        admin = User.objects.create_superuser("root", password="SenhaForte#2026")
        self.client.post(reverse("usuario_salvar"), {"id": admin.pk, "perfil": "Vendedor"})
        self.client.post(reverse("usuario_alternar", args=[admin.pk]))
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)
        self.assertEqual(perfil_do_usuario(admin), "organizador")
