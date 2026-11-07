# Sistema de Vendas e Estoque para Festas

Sistema web (Django + PostgreSQL) para controle de vendas e estoque em festas juninas
de igrejas. Telas: Login, Dashboard, Nova venda, Histórico, Produtos, Estoque,
Sugestões e Relatórios, com acesso por perfil (Organizador, Caixa e Vendedor).

## 1. O que instalar (uma vez só)

| Programa | Para quê | Observação |
|---|---|---|
| Python 3.9 ou superior (até 3.12) | rodar o projeto | marque **"Add Python to PATH"** na instalação |
| PostgreSQL | banco de dados | guarde a senha do usuário `postgres` |
| Git | baixar e enviar o código | |
| VS Code e DBeaver | editar o código e ver o banco | opcionais |

## 2. Baixar e preparar o projeto

No terminal (PowerShell), na pasta onde você quer guardar o projeto:

```
git clone <URL-DO-REPOSITORIO>
cd <NOME-DA-PASTA-DO-PROJETO>

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Linux ou Mac: troque o terceiro comando por `source venv/bin/activate`.
Sempre que abrir um terminal novo, ative o ambiente de novo (`venv\Scripts\activate`).

## 3. Criar o banco de dados

Cada pessoa tem o **seu próprio banco, no seu computador**. No DBeaver (ou no `psql`), crie um banco vazio:

```sql
CREATE DATABASE tcc;
```

Depois copie o arquivo `.env.example` para `.env` e preencha com os seus dados:

```
copy .env.example .env
```

```
DB_NAME=tcc
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
DB_HOST=localhost
DB_PORT=5432
```

O arquivo `.env` tem senhas e **nunca vai para o Git** (ele já deve estar no `.gitignore`).

## 4. Criar as tabelas e os dados iniciais

```
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
```

- `migrate` cria as tabelas no banco.
- `seed` cria os 3 usuários de teste (senha inicial `festa123`).
- `createsuperuser` cria o seu administrador para o `/admin/`.

Para ter produtos, vendas e sugestões de exemplo, rode também:

```
python manage.py seed --demo
```

(só funciona se ainda não houver produtos. `seed --demo --limpar` **apaga** produtos, vendas e festas.)

## 5. Rodar o sistema

```
python manage.py runserver
```

Abra http://127.0.0.1:8000. Para parar, use `Ctrl + C`.

Antes de vender, entre em http://127.0.0.1:8000/admin/ com o superusuário e cadastre
uma **Festa** ativa (nome, início e fim). Sem festa ativa, a tela de venda não registra.

| Usuário | Senha | O que acessa |
|---|---|---|
| organizador | festa123 | todas as telas |
| caixa | festa123 | Nova venda, Histórico e Estoque (consulta) |
| vendedor | festa123 | só Nova venda |

## 6. Testes automáticos

```
python manage.py test
```

Deve terminar com `OK`.

## 7. Trabalhando em dupla (Git)

**Ao começar a trabalhar**

```
git pull
```

Depois de um `pull`, rode o que for necessário:

| Se mudou... | Rode |
|---|---|
| `requirements.txt` | `pip install -r requirements.txt` |
| algum arquivo em `migrations/` | `python manage.py migrate` |

**Ao terminar uma parte**

```
python manage.py test
git add .
git commit -m "descreva o que foi feito"
git push
```

**Regras para evitar dor de cabeça**

- Os arquivos de `migrations/` **vão para o Git** (não coloque no `.gitignore`).
- Avise a dupla antes de mexer em `models.py`: se as duas pessoas criarem migrações no mesmo app ao mesmo tempo, dá conflito. Se acontecer o erro "Conflicting migrations", rode `python manage.py makemigrations --merge`.
- Não envie para o Git: `venv/`, `.env`, `__pycache__/` e `db.sqlite3`.
- Os dados do banco **não** são compartilhados pelo Git. Para as duas pessoas terem os mesmos dados de exemplo, use `python manage.py seed --demo`.
- Se instalar uma biblioteca nova (`pip install ...`), coloque no `requirements.txt` e envie no commit.

## 8. Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| `No module named ...` | o ambiente não está ativo: `venv\Scripts\activate`, e depois `pip install -r requirements.txt` |
| `password authentication failed` | senha errada no `.env` (`DB_PASSWORD`) |
| `database "tcc" does not exist` | crie o banco (passo 3) |
| `relation ... does not exist` | falta rodar `python manage.py migrate` |
| `TemplateDoesNotExist` | confira se as pastas `templates/` e `*/templates/` vieram do Git |
| Página de "Acesso negado" | o usuário não tem perfil: rode `python manage.py seed` |
| Venda não registra | falta uma Festa ativa no `/admin/` |

## 9. Estrutura do projeto

```
meutcc/     configurações, urls e permissoes.py (quem acessa o quê)
produtos/   cadastro de produtos e estoque
vendas/     vendas, histórico e festa
painel/     dashboard, sugestões, relatórios e login
templates/  layout comum (base.html, login.html, 403.html)
static/     CSS e JavaScript compartilhados
```
