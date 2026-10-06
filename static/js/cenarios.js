/* Cenários: simula o impacto de um choque de preço sobre a previsão e salva no banco.
   A fórmula espelha core/scenarios.py (o servidor recalcula ao salvar). */
(function () {
  const $ = (id) => document.getElementById(id);
  const { avg_price } = JSON.parse($("initial-data").textContent);
  const cfg = window.HM_SC;
  $("s-avg").textContent = HM.brl(avg_price);

  const sign = (n) => (n > 0 ? "+" : "") + n;

  function calc() {
    const volume = Math.max(0, parseFloat($("s-volume").value) || 0);
    const shock = +$("s-shock").value, hedge = +$("s-hedge").value;
    const base = avg_price * volume;
    const scen = base * (hedge / 100 + (1 - hedge / 100) * (1 + shock / 100));
    return { volume, shock, hedge, base, scen, impact: scen - base };
  }

  function render() {
    const r = calc();
    $("s-shock-v").textContent = sign(r.shock) + "%";
    $("s-hedge-v").textContent = r.hedge + "%";
    $("r-base").textContent = HM.brl0(r.base);
    $("r-scen").textContent = HM.brl0(r.scen);
    $("r-impact").textContent = (r.impact > 0 ? "+" : "") + HM.brl0(r.impact);
    const pct = r.base ? (r.impact / r.base) * 100 : 0;
    const chip = $("r-chip");
    chip.className = "chip " + (r.impact > 0 ? "down" : "");   // custo maior = ruim
    chip.innerHTML = HM.icon(r.impact > 0 ? "i-up" : "i-down") + `<span>${HM.pct1(pct)} no custo</span>`;
    const mx = Math.max(r.base, r.scen) || 1;
    $("bar-base").style.width = (r.base / mx) * 100 + "%";
    $("bar-scen").style.width = (r.scen / mx) * 100 + "%";
  }
  ["s-volume", "s-shock", "s-hedge"].forEach((id) => $(id).addEventListener("input", render));
  render();

  $("s-save").addEventListener("click", async () => {
    const r = calc(), msg = $("s-msg");
    if (!r.volume) { msg.textContent = "Informe um volume maior que zero."; return; }
    try {
      const res = await fetch(cfg.saveUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
        credentials: "same-origin",
        body: JSON.stringify({ commodity: cfg.commodity, name: $("s-name").value, price_shock: r.shock, volume: r.volume, hedge: r.hedge }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.status);
      const tr = document.createElement("tr");
      tr.className = "fresh";
      tr.innerHTML = `<td><b>${HM.esc(data.name)}</b></td><td>${HM.esc(data.commodity)}</td>
        <td class="num">${HM.pct1(data.price_shock)}</td><td class="num">${data.hedge}%</td>
        <td class="num">${HM.brl(data.baseline)}</td><td class="num">${HM.brl(data.scenario)}</td>
        <td class="num ${data.impact > 0 ? "down-txt" : "up-txt"}"><b>${HM.brl(data.impact)}</b></td>`;
      $("saved").prepend(tr);
      $("saved-empty").hidden = true;
      $("s-name").value = "";
      msg.textContent = "Cenário salvo.";
    } catch (e) {
      msg.textContent = "Não foi possível salvar: " + e.message;
    }
  });
})();
