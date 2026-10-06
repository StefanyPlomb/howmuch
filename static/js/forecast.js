/* Previsões: gráfico histórico + previsão com faixa de incerteza (SVG) */
(function () {
  const $ = (id) => document.getElementById(id);
  const SVG_NS = "http://www.w3.org/2000/svg";
  const { unit, series } = JSON.parse($("initial-data").textContent);
  const hist = series.filter((p) => !p.forecast);
  const fc = series.filter((p) => p.forecast);
  const last = hist[hist.length - 1];
  const end = fc[fc.length - 1];
  const avg = fc.reduce((s, p) => s + p.value, 0) / fc.length;
  const monthFmt = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" });
  const fmtMonth = (iso) => monthFmt.format(new Date(iso + "T00:00:00Z")).replace(".", "");
  const delta = (v) => ((v - last.value) / last.value) * 100;

  // ---------- KPIs ----------
  $("f-last").textContent = HM.brl(last.value);
  $("f-end").textContent = HM.brl(end.value);
  $("f-avg").textContent = HM.brl(avg);
  $("f-range").textContent = `${HM.brl0(end.low)} – ${HM.brl0(end.high)}`;
  const chip = $("f-end-delta"), d = delta(end.value);
  chip.className = "chip " + (d < 0 ? "down" : "");
  chip.innerHTML = HM.icon(d < 0 ? "i-down" : "i-up") + `<span>${HM.pct1(d)} vs. último preço</span>`;

  // ---------- tabela ----------
  $("ftable").innerHTML = fc.map((p) => {
    const dv = delta(p.value);
    return `<tr><td>${HM.esc(fmtMonth(p.month))}</td><td class="num"><b>${HM.brl(p.value)}</b></td>
      <td class="num muted">${HM.brl(p.low)}</td><td class="num muted">${HM.brl(p.high)}</td>
      <td class="num ${dv < 0 ? "down-txt" : "up-txt"}">${HM.pct1(dv)}</td></tr>`;
  }).join("");

  // ---------- gráfico ----------
  const chartEl = $("fchart");
  const tip = document.createElement("div");
  tip.className = "tip";
  chartEl.appendChild(tip);
  let hover = null;

  const el = (name, attrs) => {
    const n = document.createElementNS(SVG_NS, name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  };

  function render() {
    const W = chartEl.clientWidth, H = chartEl.clientHeight;
    if (!W || !H) return;
    const m = { t: 14, r: 14, b: 28, l: 64 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const all = series.flatMap((p) => [p.value, p.low ?? p.value, p.high ?? p.value]);
    let lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const x = (i) => m.l + (i / (series.length - 1)) * iw;
    const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * ih;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });

    for (let g = 0; g <= 4; g++) {
      const v = lo + ((hi - lo) * g) / 4, gy = y(v);
      svg.appendChild(el("line", { class: "grid-line", x1: m.l, x2: W - m.r, y1: gy, y2: gy }));
      const t = el("text", { class: "axis", x: m.l - 10, y: gy + 4, "text-anchor": "end" });
      t.textContent = HM.brl0(v);
      svg.appendChild(t);
    }
    [0, Math.floor(series.length / 4), Math.floor(series.length / 2), Math.floor((series.length * 3) / 4), series.length - 1].forEach((i, n, a) => {
      const t = el("text", { class: "axis", x: x(i), y: H - 8, "text-anchor": n === 0 ? "start" : n === a.length - 1 ? "end" : "middle" });
      t.textContent = fmtMonth(series[i].month);
      svg.appendChild(t);
    });

    const off = hist.length - 1; // índice do último ponto histórico
    const fcPts = series.slice(off);
    // faixa de incerteza (parte da previsão, ancorada no último preço)
    const upper = fcPts.map((p, k) => `${x(off + k).toFixed(1)},${y(p.high ?? p.value).toFixed(1)}`);
    const lower = fcPts.map((p, k) => `${x(off + k).toFixed(1)},${y(p.low ?? p.value).toFixed(1)}`).reverse();
    svg.appendChild(el("path", { class: "band", d: "M" + upper.join(" L") + " L" + lower.join(" L") + " Z" }));

    // divisor "hoje"
    svg.appendChild(el("line", { class: "today", x1: x(off), x2: x(off), y1: m.t, y2: m.t + ih }));

    svg.appendChild(el("path", { class: "line", d: "M" + series.slice(0, off + 1).map((p, i) => `${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" L") }));
    svg.appendChild(el("path", { class: "line fc", d: "M" + fcPts.map((p, k) => `${x(off + k).toFixed(1)},${y(p.value).toFixed(1)}`).join(" L") }));

    const focus = hover ?? off;
    if (hover !== null) svg.appendChild(el("line", { class: "cursor", x1: x(focus), x2: x(focus), y1: m.t, y2: m.t + ih }));
    svg.appendChild(el("circle", { class: "dot", cx: x(focus), cy: y(series[focus].value), r: 5 }));

    const hit = el("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => {
      const box = svg.getBoundingClientRect();
      hover = Math.max(0, Math.min(series.length - 1, Math.round(((ev.clientX - box.left - m.l) / iw) * (series.length - 1))));
      render();
      const p = series[hover];
      tip.innerHTML = `<b>${HM.brl(p.value)}</b><span>${HM.esc(fmtMonth(p.month))} · ${p.forecast ? "previsão" : "histórico"}</span>` +
        (p.forecast ? `<span>${HM.brl0(p.low)} – ${HM.brl0(p.high)}</span>` : "");
      tip.style.left = x(hover) + "px"; tip.style.top = y(p.value) + "px"; tip.style.opacity = 1;
    });
    hit.addEventListener("mouseleave", () => { hover = null; tip.style.opacity = 0; render(); });
    svg.appendChild(hit);

    chartEl.querySelector("svg")?.remove();
    chartEl.prepend(svg);
  }

  render();
  new ResizeObserver(render).observe(chartEl);
  window.addEventListener("hm:theme", render);
})();
