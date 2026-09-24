/* Dashboard: consome /api/telemetria/ a cada 3 s e redesenha os painéis */
(function () {
  const $ = (id) => document.getElementById(id);
  const POLL_MS = 3000;
  const SVG_NS = "http://www.w3.org/2000/svg";

  let data = JSON.parse($("initial-data").textContent);
  let knownFeed = new Set();
  let failures = 0;

  // ---------- KPIs ----------
  function deltaChip(el, v, label) {
    el.className = "chip " + (v < 0 ? "down" : "");
    el.innerHTML = HM.icon(v < 0 ? "i-down" : "i-up") + `<span>${HM.pct(v)}${label ? " " + label : ""}</span>`;
  }

  function renderKpis(k) {
    $("k-total").textContent = HM.brl(k.total);
    deltaChip($("k-total-delta"), k.total_delta, "vs. leitura anterior");
    $("k-hourly").textContent = HM.brl(k.hourly_cost);
    $("k-range").textContent = `mín ${HM.brl0(k.low)} · máx ${HM.brl0(k.peak)}`;
    $("k-rpm").textContent = HM.int(k.readings_per_min);
    $("k-sources").textContent = k.sources_online;
    $("k-alerts").textContent = k.alerts;
    deltaChip($("c-delta"), k.window_delta, "na janela");
  }

  // ---------- gráfico de linha (SVG) ----------
  const chartEl = $("chart");
  const tip = document.createElement("div");
  tip.className = "tip";
  chartEl.appendChild(tip);
  let hoverIdx = null;

  function el(name, attrs) {
    const n = document.createElementNS(SVG_NS, name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function renderChart(series) {
    const W = chartEl.clientWidth, H = chartEl.clientHeight;
    if (!W || !H) return;
    const m = { t: 12, r: 12, b: 26, l: 62 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;

    const vs = series.map((p) => p.v);
    let lo = Math.min(...vs), hi = Math.max(...vs);
    const padY = (hi - lo) * 0.12 || 1;
    lo -= padY; hi += padY;

    const x = (i) => m.l + (i / (series.length - 1)) * iw;
    const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * ih;

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });
    const defs = el("defs", {});
    const grad = el("linearGradient", { id: "areaGrad", x1: 0, y1: 0, x2: 0, y2: 1 });
    grad.append(
      el("stop", { offset: 0, "stop-color": "var(--olive-strong)", "stop-opacity": 0.30 }),
      el("stop", { offset: 1, "stop-color": "var(--olive-strong)", "stop-opacity": 0 })
    );
    defs.appendChild(grad);
    svg.appendChild(defs);

    // grade horizontal + rótulos do eixo Y
    for (let g = 0; g <= 4; g++) {
      const v = lo + ((hi - lo) * g) / 4;
      const gy = y(v);
      svg.appendChild(el("line", { class: "grid-line", x1: m.l, x2: W - m.r, y1: gy, y2: gy }));
      const label = el("text", { class: "axis", x: m.l - 10, y: gy + 4, "text-anchor": "end" });
      label.textContent = HM.brl0(v);
      svg.appendChild(label);
    }

    // rótulos do eixo X (início, meio, fim)
    [0, Math.floor((series.length - 1) / 2), series.length - 1].forEach((i, n) => {
      const label = el("text", {
        class: "axis", x: x(i), y: H - 6,
        "text-anchor": n === 0 ? "start" : n === 2 ? "end" : "middle",
      });
      label.textContent = HM.time(series[i].t);
      svg.appendChild(label);
    });

    const pts = series.map((p, i) => `${x(i).toFixed(1)},${y(p.v).toFixed(1)}`);
    const linePath = "M" + pts.join(" L");
    svg.appendChild(el("path", { d: `${linePath} L${x(series.length - 1)},${m.t + ih} L${x(0)},${m.t + ih} Z`, fill: "url(#areaGrad)" }));
    svg.appendChild(el("path", { class: "line", d: linePath }));

    const focus = hoverIdx ?? series.length - 1;
    if (hoverIdx !== null) {
      svg.appendChild(el("line", { class: "cursor", x1: x(focus), x2: x(focus), y1: m.t, y2: m.t + ih }));
    }
    svg.appendChild(el("circle", { class: "dot", cx: x(focus), cy: y(series[focus].v), r: 5 }));

    // hover
    const hit = el("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent" });
    hit.addEventListener("mousemove", (ev) => {
      const box = svg.getBoundingClientRect();
      const rel = (ev.clientX - box.left - m.l) / iw;
      hoverIdx = Math.max(0, Math.min(series.length - 1, Math.round(rel * (series.length - 1))));
      renderChart(data.series);
      showTip(series[hoverIdx], x(hoverIdx), y(series[hoverIdx].v));
    });
    hit.addEventListener("mouseleave", () => {
      hoverIdx = null;
      tip.style.opacity = 0;
      renderChart(data.series);
    });
    svg.appendChild(hit);

    chartEl.querySelector("svg")?.remove();
    chartEl.prepend(svg);
  }

  function showTip(p, px, py) {
    tip.innerHTML = `<b>${HM.brl(p.v)}</b><span>${HM.time(p.t)}</span>`;
    tip.style.left = px + "px";
    tip.style.top = py + "px";
    tip.style.opacity = 1;
  }

  // ---------- categorias ----------
  function renderCategories(cats) {
    const total = cats.reduce((s, c) => s + c.value, 0);
    const max = Math.max(...cats.map((c) => c.value));
    $("cats").innerHTML = cats.map((c) => `
      <li>
        <div class="row"><b>${HM.esc(c.name)}</b><span>${HM.brl0(c.value)}</span></div>
        <div class="bar"><i style="width:${(c.value / max) * 100}%"></i></div>
        <div class="meta"><span>${((c.value / total) * 100).toFixed(1).replace(".", ",")}% do total</span>
          <span class="${c.delta < 0 ? "down-txt" : "up-txt"}">${HM.pct1(c.delta)}</span></div>
      </li>`).join("");
  }

  // ---------- leituras recentes ----------
  const STATUS = { ok: "Normal", atencao: "Atenção", critico: "Crítico" };

  function renderFeed(feed) {
    const fresh = new Set();
    $("feed").innerHTML = feed.map((f) => {
      const isNew = knownFeed.size && !knownFeed.has(f.id);
      fresh.add(f.id);
      return `<tr class="${isNew ? "fresh" : ""}">
        <td class="id">${HM.esc(f.id)}</td>
        <td>${HM.esc(f.source)}</td>
        <td>${HM.esc(f.kind)}</td>
        <td class="num"><b>${HM.brl(f.value)}</b></td>
        <td class="num ${f.delta < 0 ? "down-txt" : "up-txt"}">${HM.pct1(f.delta)}</td>
        <td><span class="status ${f.status}">${STATUS[f.status]}</span></td>
        <td class="muted">${HM.time(f.at)}</td>
      </tr>`;
    }).join("");
    knownFeed = fresh;
  }

  // ---------- ciclo ----------
  function render() {
    renderKpis(data.kpis);
    renderChart(data.series);
    renderCategories(data.categories);
    renderFeed(data.feed);
    $("updated").textContent = HM.time(data.generated_at);
    const first = data.series[0].t, last = data.series[data.series.length - 1].t;
    $("c-window").textContent = Math.round((last - first) / 60 * 10) / 10 + " min";
  }

  async function poll() {
    try {
      const r = await fetch("/api/telemetria/", { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (r.status === 401 || r.status === 403 || r.redirected) { location.reload(); return; }
      if (!r.ok) throw new Error(r.status);
      data = await r.json();
      failures = 0;
      $("live-tag").classList.remove("stale");
      render();
    } catch (e) {
      if (++failures >= 2) $("live-tag").classList.add("stale");
    }
  }

  render();
  setInterval(poll, POLL_MS);
  new ResizeObserver(() => renderChart(data.series)).observe(chartEl);
  window.addEventListener("hm:theme", () => renderChart(data.series));
})();
