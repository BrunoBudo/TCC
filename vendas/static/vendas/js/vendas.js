// Tela de Nova venda: carrinho no navegador + envio para o servidor.
(function () {
  var carrinho = {};
  var forma = "pix";
  var produtos = {};

  function brl(v) { return "R$ " + v.toFixed(2).replace(".", ","); }

  function aviso(texto, erro) {
    var caixa = document.getElementById("toasts");
    var m = document.createElement("div");
    m.className = "msg" + (erro ? " error" : "");
    m.textContent = texto;
    caixa.appendChild(m);
    setTimeout(function () { m.remove(); }, 4000);
  }

  // Função fallback para buscar o CSRF Token via cookie caso não ache o input
  function getCsrfToken() {
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  document.querySelectorAll(".prod").forEach(function (b) {
    produtos[b.dataset.id] = {
      nome: b.dataset.nome,
      preco: parseFloat(b.dataset.preco),
      estoque: parseInt(b.dataset.estoque, 10)
    };
    b.addEventListener("click", function () { mudar(b.dataset.id, 1); });
  });

  function mudar(id, delta) {
    var p = produtos[id];
    var q = (carrinho[id] || 0) + delta;
    if (q > p.estoque) { aviso("Só há " + p.estoque + " de " + p.nome + " em estoque.", true); return; }
    if (q <= 0) { delete carrinho[id]; } else { carrinho[id] = q; }
    desenhar();
  }

  function botao(texto, rotulo, fn) {
    var b = document.createElement("button");
    b.type = "button"; b.textContent = texto; b.setAttribute("aria-label", rotulo);
    b.addEventListener("click", fn);
    return b;
  }

  function desenhar() {
    var lista = document.getElementById("cl");
    var total = 0;
    lista.innerHTML = "";
    var ids = Object.keys(carrinho);
    if (!ids.length) {
      var vazio = document.createElement("div");
      vazio.className = "empty";
      vazio.textContent = "Carrinho vazio. Toque em um produto para começar.";
      lista.appendChild(vazio);
    }
    ids.forEach(function (id) {
      var p = produtos[id];
      total += p.preco * carrinho[id];
      var linha = document.createElement("div");
      linha.className = "line";
      var nome = document.createElement("span");
      nome.textContent = p.nome + " · " + brl(p.preco);
      var qtd = document.createElement("span");
      qtd.className = "qty";
      qtd.appendChild(botao("−", "Remover um", function () { mudar(id, -1); }));
      qtd.appendChild(document.createTextNode(carrinho[id]));
      qtd.appendChild(botao("+", "Adicionar um", function () { mudar(id, 1); }));
      linha.appendChild(nome);
      linha.appendChild(qtd);
      lista.appendChild(linha);
    });
    document.getElementById("ct").textContent = brl(total);
  }

  document.querySelectorAll("#pay button").forEach(function (b) {
    b.addEventListener("click", function () {
      forma = b.dataset.forma;
      document.querySelectorAll("#pay button").forEach(function (x) { x.classList.toggle("on", x === b); });
    });
  });

  document.getElementById("fin").addEventListener("click", function () {
    var botaoFin = this;
    var itens = Object.keys(carrinho).map(function (id) { return { produto_id: parseInt(id, 10), quantidade: carrinho[id] }; });
    if (!itens.length) { aviso("Adicione ao menos um produto.", true); return; }
    botaoFin.disabled = true;

    // Obtém o token garantido do input ou dos cookies
    var token = getCsrfToken();

    fetch(botaoFin.dataset.url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ forma: forma, itens: itens })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok) { location.reload(); }
        else { aviso(res.d.erro || "Não foi possível registrar a venda.", true); botaoFin.disabled = false; }
      })
      .catch(function () { aviso("Erro de conexão com o servidor.", true); botaoFin.disabled = false; });
  });

  desenhar();
})();