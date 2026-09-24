/* Utilidades compartilhadas: tema e formatação pt-BR */
(function () {
  const root = document.documentElement;

  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("hm-theme", next); } catch (e) {}
      window.dispatchEvent(new CustomEvent("hm:theme", { detail: next }));
    });
  });

  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const brl0 = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const int = new Intl.NumberFormat("pt-BR");
  const pct = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: "exceptZero" });
  const pct1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" });

  window.HM = {
    brl: (v) => brl.format(v),
    brl0: (v) => brl0.format(v),
    int: (v) => int.format(v),
    pct: (v) => pct.format(v) + "%",
    pct1: (v) => pct1.format(v) + "%",
    time: (epochSeconds) => new Date(epochSeconds * 1000).toLocaleTimeString("pt-BR"),
    icon: (id) => `<svg class="ico" aria-hidden="true"><use href="#${id}"/></svg>`,
    esc: (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
  };
})();
