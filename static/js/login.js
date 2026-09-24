/* Tela de login: mostrar/ocultar senha, estado de envio e telemetria demonstrativa */
(function () {
  document.getElementById("year").textContent = new Date().getFullYear();

  // --- mostrar / ocultar senha
  const pass = document.getElementById("id_password");
  const toggle = document.getElementById("toggle-pass");
  toggle.addEventListener("click", () => {
    const show = pass.type === "password";
    pass.type = show ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(show));
    toggle.setAttribute("aria-label", show ? "Ocultar senha" : "Mostrar senha");
  });

  // --- evita duplo envio
  document.getElementById("login-form").addEventListener("submit", () => {
    const btn = document.getElementById("submit-btn");
    btn.disabled = true;
    btn.querySelector("span").textContent = "Entrando…";
  });

  // --- telemetria demonstrativa (100% fictícia, gerada aqui no navegador)
  const N = 40;
  const cats = [
    { name: "Infraestrutura", base: 58000 },
    { name: "Energia", base: 34500 },
    { name: "Logística", base: 41200 },
  ];
  let t = 0;
  const series = [];
  const value = (i) => 322000 + 21000 * Math.sin(i / 9) + 7000 * Math.sin(i / 2.7) + (Math.random() - 0.5) * 3500;
  for (let i = 0; i < N; i++) series.push(value(t++));

  const elValue = document.getElementById("demo-value");
  const elDelta = document.getElementById("demo-delta");
  const elClock = document.getElementById("demo-clock");
  const elSpark = document.getElementById("demo-spark");
  const elBars = document.getElementById("demo-bars");

  elBars.innerHTML = cats.map((c) =>
    `<li><span>${c.name}</span><span class="bar"><i style="width:0"></i></span><b class="v">—</b></li>`
  ).join("");

  function drawSpark() {
    const W = 320, H = 70, pad = 4;
    const min = Math.min(...series), max = Math.max(...series);
    const x = (i) => (i / (N - 1)) * W;
    const y = (v) => H - pad - ((v - min) / (max - min || 1)) * (H - pad * 2);
    const line = series.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    elSpark.innerHTML =
      `<defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
         <stop offset="0" stop-color="var(--olive-strong)" stop-opacity=".32"/>
         <stop offset="1" stop-color="var(--olive-strong)" stop-opacity="0"/>
       </linearGradient></defs>
       <path class="area" d="${line} L${W},${H} L0,${H} Z" fill="url(#sg)"/>
       <path class="line" d="${line}"/>`;
  }

  function tick() {
    series.push(value(t++));
    series.shift();
    const cur = series[N - 1], prev = series[N - 2];
    const d = ((cur - prev) / prev) * 100;

    elValue.textContent = HM.brl(cur);
    elDelta.className = "chip " + (d >= 0 ? "up" : "down");
    elDelta.innerHTML = HM.icon(d >= 0 ? "i-up" : "i-down") + `<span>${HM.pct(d)}</span>`;
    elClock.textContent = new Date().toLocaleTimeString("pt-BR");
    drawSpark();

    const vals = cats.map((c, k) => c.base * (1 + 0.14 * Math.sin(t / (6 + k * 3) + k)));
    const top = Math.max(...vals) * 1.15;
    elBars.querySelectorAll("li").forEach((li, k) => {
      li.querySelector("i").style.width = (vals[k] / top) * 100 + "%";
      li.querySelector(".v").textContent = HM.brl0(vals[k]);
    });
  }

  tick();
  setInterval(tick, 2000);
})();
