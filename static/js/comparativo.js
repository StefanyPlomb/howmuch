/* Comparativo: linhas base 100 de todas as commodities (SVG) */
(function () {
  const $ = (id) => document.getElementById(id);
  const SVG_NS = "http://www.w3.org/2000/svg";
  const { series } = JSON.parse($("initial-data").textContent);
  const COLORS = ["var(--olive-strong)", "#d9a441", "#6fa8c9", "#c86a55"];
  const chartEl = $("cchart");
  const tip = document.createElement("div");
  tip.className = "tip";
  chartEl.appendChild(tip);
  const monthFmt = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" });
  const fmtMonth = (iso) => monthFmt.format(new Date(iso + "T00:00:00Z")).replace(".", "");
  const n = series[0].points.length;
  let hover = null;

  $("cmp-legend").innerHTML = series
    .map((s, i) => `<span><i class="lg" style="border-color:${COLORS[i % COLORS.length]}"></i>${HM.esc(s.name)}</span>`).join(" ");

  const el = (name, attrs) => {
    const e = document.createElementNS(SVG_NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  };

  function render() {
    const W = chartEl.clientWidth, H = chartEl.clientHeight;
    if (!W || !H) return;
    const m = { t: 14, r: 14, b: 28, l: 44 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const all = series.flatMap((s) => s.points.map((p) => p.v));
    let lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const x = (i) => m.l + (i / (n - 1)) * iw;
    const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * ih;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });

    for (let g = 0; g <= 4; g++) {
      const v = lo + ((hi - lo) * g) / 4, gy = y(v);
      svg.appendChild(el("line", { class: "grid-line", x1: m.l, x2: W - m.r, y1: gy, y2: gy }));
      const t = el("text", { class: "axis", x: m.l - 8, y: gy + 4, "text-anchor": "end" });
      t.textContent = Math.round(v);
      svg.appendChild(t);
    }
    [0, Math.floor(n / 2), n - 1].forEach((i, k) => {
      const t = el("text", { class: "axis", x: x(i), y: H - 8, "text-anchor": k === 0 ? "start" : k === 2 ? "end" : "middle" });
      t.textContent = fmtMonth(series[0].points[i].month);
      svg.appendChild(t);
    });

    const firstFc = series[0].points.findIndex((p) => p.forecast);
    if (firstFc > 0) svg.appendChild(el("line", { class: "today", x1: x(firstFc - 1), x2: x(firstFc - 1), y1: m.t, y2: m.t + ih }));

    series.forEach((s, si) => {
      const color = COLORS[si % COLORS.length];
      const cut = firstFc > 0 ? firstFc - 1 : n - 1;
      const d = (from, to) => "M" + s.points.slice(from, to + 1).map((p, k) => `${x(from + k).toFixed(1)},${y(p.v).toFixed(1)}`).join(" L");
      svg.appendChild(el("path", { class: "line", d: d(0, cut), style: `stroke:${color}` }));
      if (cut < n - 1) svg.appendChild(el("path", { class: "line fc", d: d(cut, n - 1), style: `stroke:${color}` }));
      if (hover !== null) svg.appendChild(el("circle", { class: "dot", cx: x(hover), cy: y(s.points[hover].v), r: 4, style: `stroke:${color}` }));
    });
    if (hover !== null) svg.appendChild(el("line", { class: "cursor", x1: x(hover), x2: x(hover), y1: m.t, y2: m.t + ih }));

    const hit = el("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => {
      const box = svg.getBoundingClientRect();
      hover = Math.max(0, Math.min(n - 1, Math.round(((ev.clientX - box.left - m.l) / iw) * (n - 1))));
      render();
      tip.innerHTML = `<span>${HM.esc(fmtMonth(series[0].points[hover].month))}</span>` +
        series.map((s) => `<b style="font-size:12.5px">${HM.esc(s.name)}: ${s.points[hover].v.toFixed(1).replace(".", ",")}</b>`).join("");
      tip.style.left = x(hover) + "px"; tip.style.top = m.t + 40 + "px"; tip.style.opacity = 1;
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
