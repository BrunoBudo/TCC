function abrirModal(id) {
  var m = document.getElementById(id);
  if (!m) return;
  m.classList.add("show");
  var campo = m.querySelector("input:not([type=hidden]), select");
  if (campo) campo.focus();
}
function fecharModal(id) {
  document.getElementById(id).classList.remove("show");
}
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal.show").forEach(function (m) { m.classList.remove("show"); });
  }
});
setTimeout(function () {
  document.querySelectorAll(".msg").forEach(function (m) { m.remove(); });
}, 5000);
