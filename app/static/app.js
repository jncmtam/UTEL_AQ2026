/* AGQO prototype front-end. Talks to app/server.py; every chart is ECharts, the circuit is hand-drawn SVG. */
"use strict";

const C = { bg: "#070b14", card: "#101a2c", line: "#1e2b44", text: "#e6edf7", muted: "#8b9ab3",
  up: "#22c55e", down: "#ef4444", amber: "#f59e0b", ai: "#38bdf8", q: "#a78bfa", cl: "#34d399", accent: "#facc15", grey: "#64748b" };
const SECTOR_VI = { Banking: "Ngân hàng", Insurance: "Bảo hiểm", Technology: "Công nghệ", Energy: "Năng lượng",
  Materials: "Nguyên vật liệu", "Real estate": "Bất động sản", Consumer: "Tiêu dùng", Brokerage: "Chứng khoán", Aviation: "Hàng không" };
const PORT_VI = { "ideal (fractional shares)": "Lý tưởng (cổ phiếu lẻ)", "nearest-lot rounding": "Làm tròn lô gần nhất",
  "greedy lot filling": "Tham lam (thêm từng lô)", "AGQO": "AGQO" };
const PORT_COLOR = { "ideal (fractional shares)": C.grey, "nearest-lot rounding": C.down, "greedy lot filling": C.amber, "AGQO": C.ai };
const BIN_VI = { "optimal": "Tối ưu", "within 5%": "Trong 5%", "5–25%": "5–25%", "25–100%": "25–100%", "worse than typical": "Tệ hơn trung bình", "over budget": "Vượt ngân sách" };
const BIN_COLOR = { "optimal": "#16a34a", "within 5%": "#4ade80", "5–25%": "#facc15", "25–100%": "#f97316", "worse than typical": "#ef4444", "over budget": "#334155" };
const ARM_VI = { "AGQO": "AGQO", "warm start only": "Khởi động ấm (cổ điển)", "textbook QAOA": "QAOA sách giáo khoa", "random guessing": "Đoán ngẫu nhiên" };
const FEAT_VI = { warm_confidence: "Độ tự tin khởi động ấm", decided_share: "Tỷ lệ qubit đã rõ", log_field_to_coupling: "Trường / tương tác (log)",
  coupling_concentration: "Độ tập trung tương tác", lot_weight_pct: "Cỡ lô (% vốn)" };

const $ = (s) => document.querySelector(s);
const fmt = (x, d = 1) => Number(x).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
const vnd = (x) => Math.round(x).toLocaleString("vi-VN");
const charts = {};
let META = null, LAST = null;

function chart(id) {
  if (charts[id]) charts[id].dispose();
  charts[id] = echarts.init(document.getElementById(id), null, { renderer: "canvas" });
  return charts[id];
}
window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));
const AX = { axisLine: { lineStyle: { color: C.line } }, axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: "#152036" } } };
const BASE = { backgroundColor: "transparent", textStyle: { color: C.text, fontFamily: "Be Vietnam Pro" },
  tooltip: { backgroundColor: C.card, borderColor: C.line, textStyle: { color: C.text } }, animationDuration: 1200, animationEasing: "cubicOut" };
const LEG = { textStyle: { color: C.muted }, top: 0 };

function toast(msg, ms = 4000) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), ms); }
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

/* ---------------- reveal + counters ---------------- */
const io = new IntersectionObserver((es) => es.forEach((e) => {
  if (!e.isIntersecting) return;
  e.target.classList.add("in");
  e.target.querySelectorAll("[data-count]").forEach(countUp);
  io.unobserve(e.target);
}), { threshold: 0.12 });
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
function countUp(el) {
  const to = parseFloat(el.dataset.count), dec = +el.dataset.dec, t0 = performance.now();
  const step = (t) => { const k = Math.min(1, (t - t0) / 1400), v = to * (1 - Math.pow(1 - k, 3));
    el.textContent = fmt(v, dec); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

/* ---------------- 1. lot-cost chart ---------------- */
function lotChart(cap) {
  const s = META.stocks, pct = s.map((x) => 100 * x.lot_vnd / (cap * 1e6));
  const c = chart("lotChart");
  c.setOption({ ...BASE, grid: { left: 50, right: 20, top: 30, bottom: 60 },
    tooltip: { ...BASE.tooltip, trigger: "axis", formatter: (p) => `${p[0].name} · ${SECTOR_VI[s[p[0].dataIndex].sector]}<br>1 lô = ${vnd(s[p[0].dataIndex].lot_vnd)} đ<br><b>${fmt(p[0].value)}%</b> số vốn` },
    xAxis: { type: "category", data: s.map((x) => x.ticker), ...AX, axisLabel: { color: C.muted, rotate: 60, fontFamily: "JetBrains Mono", fontSize: 11 } },
    yAxis: { type: "value", name: "% số vốn", nameTextStyle: { color: C.muted }, ...AX, max: (v) => Math.max(110, Math.ceil(v.max / 10) * 10) },
    series: [{ type: "bar", data: pct.map((v) => ({ value: +v.toFixed(2), itemStyle: { color: v > 100 ? C.down : v > 10 ? C.amber : C.up, borderRadius: [4, 4, 0, 0] } })),
      markLine: { symbol: "none", label: { color: C.text, formatter: "{b}" }, lineStyle: { type: "dashed" },
        data: [{ yAxis: 100, name: "toàn bộ số vốn", lineStyle: { color: C.down } }, { yAxis: 10, name: "10%", lineStyle: { color: C.amber } }] } }] });
  const over10 = pct.filter((v) => v > 10).length, over100 = pct.filter((v) => v > 100).length;
  $("#lotCaption").innerHTML = `Hình 1. Giá một lô (100 cổ phiếu) của ${s.length} mã VN30 theo % số vốn ${cap} triệu, ngày ${META.date}. ` +
    `<b class="amber">${over10}</b> mã có một lô vượt 10% số vốn${over100 ? `, <b class="down">${over100}</b> mã vượt toàn bộ số vốn` : ""}.`;
}

/* ---------------- pipeline stepper ---------------- */
function stepTo(n) { document.querySelectorAll(".step").forEach((s) => { const k = +s.dataset.s; s.classList.toggle("done", k < n); s.classList.toggle("active", k === n); }); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function showPanel(i) { stepTo(i); const p = $(`#p${i}`); p.classList.add("show"); await sleep(380); }

/* ---------------- 1. mandate ---------------- */
function mandateChips(m) {
  const out = [];
  if (m.exclude_tickers?.length) out.push(`Loại mã: ${m.exclude_tickers.join(", ")}`);
  if (m.exclude_sectors?.length) out.push(`Loại ngành: ${m.exclude_sectors.map((s) => SECTOR_VI[s] || s).join(", ")}`);
  for (const [s, c] of Object.entries(m.sector_caps || {})) out.push(`${SECTOR_VI[s] || s} ≤ ${fmt(100 * c, 0)}%`);
  if (m.max_weight_per_stock != null) out.push(`Mỗi mã ≤ ${fmt(100 * m.max_weight_per_stock, 0)}%`);
  if (m.max_holdings != null) out.push(`Tối đa ${m.max_holdings} mã`);
  if (m.min_cash_pct != null) out.push(`Tiền mặt ≥ ${fmt(m.min_cash_pct, 0)}%`);
  return out;
}
function renderMandate(res) {
  const chips = mandateChips(res.mandate);
  $("#mandateChips").innerHTML = chips.length ? chips.map((c) => `<span class="chip">${c}</span>`).join("") : `<span class="chip none">Không có ràng buộc: bám VN30 đầy đủ</span>`;
  const live = res.source.includes("live") || res.source.includes("logged");
  $("#mandateSource").innerHTML = `Nguồn: <b style="color:${live ? C.ai : C.amber}">${res.source}</b>${res.llm_note ? " · " + res.llm_note : ""}`;
  $("#mandateJson").textContent = JSON.stringify(res.raw || res.mandate, null, 2);
  $("#clarify").innerHTML = res.needs_clarification && res.question ? `<div class="bubble">🤖 LLM hỏi lại: “${res.question}”<br><small>Yêu cầu chưa đủ rõ để thành ràng buộc; AGQO chạy với danh mục bám VN30 đầy đủ cho đến khi bạn trả lời.</small></div>` : "";
}

/* ---------------- 2. market ---------------- */
function renderMarket(d) {
  const m = d.market;
  $("#marketKpis").innerHTML = [
    [fmt(m.effective_bets), "số “cược” độc lập thực sự trong VN30 (không phải 30)"],
    [fmt(m.market_factor_share_pct) + "%", "phương sai do một nhân tố thị trường chung"],
    [fmt(m.avg_correlation, 2), "tương quan trung bình giữa các cặp mã"],
    [fmt(m.lot_cost_pct_max) + "%", `lô đắt nhất so với ${fmt(d.capital_vnd / 1e6, 0)} triệu vốn`]]
    .map(([v, l]) => `<div class="k"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  $("#clusters").innerHTML = m.clusters.filter((c) => c.length > 1).map((c) => `<div class="cluster">${c.map((t) => `<span>${t}</span>`).join("")}</div>`).join("") +
    `<div class="cluster" style="border-style:solid;opacity:.7">${m.clusters.filter((c) => c.length === 1).map((c) => `<span style="background:#1b2740">${c[0]}</span>`).join("")}</div>`;
}

/* ---------------- 3. Hamiltonian ---------------- */
function renderHamiltonian(d) {
  katex.render(String.raw`E(\mathbf{x}) = \underbrace{252\,(w^\top\Sigma w - 2\,w^\top c + \sigma_b^2)}_{\text{sai số bám}^2} + \underbrace{\gamma\,\lVert w - w_{\text{cũ}}\rVert^2}_{\text{vòng quay}} + \underbrace{\lambda\,(\mathbf{1}^\top w - t)^2}_{\text{ngân sách}},\quad w = w_0 + A\mathbf{x},\ \mathbf{x}\in\{0,1\}^{${d.register.length}}`, $("#eq"), { displayMode: true, throwOnError: false });
  const n = d.register.length, tk = d.register.map((r) => r.ticker), J = d.hamiltonian.J;
  const data = [], mx = Math.max(...J.flat().map(Math.abs)) || 1;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) data.push([j, i, +(J[i][j] / mx).toFixed(3)]);
  chart("jHeat").setOption({ ...BASE, grid: { left: 54, right: 20, top: 10, bottom: 70 },
    tooltip: { ...BASE.tooltip, formatter: (p) => `${tk[p.value[1]]} – ${tk[p.value[0]]}<br>J (chuẩn hoá) = ${p.value[2]}` },
    xAxis: { type: "category", data: tk, ...AX, axisLabel: { color: C.muted, rotate: 70, fontSize: 10, fontFamily: "JetBrains Mono" } },
    yAxis: { type: "category", data: tk, ...AX, axisLabel: { color: C.muted, fontSize: 10, fontFamily: "JetBrains Mono" } },
    visualMap: { min: -1, max: 1, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemHeight: 140, textStyle: { color: C.muted },
      inRange: { color: ["#2563eb", "#0f172a", "#ef4444"] } },
    series: [{ type: "heatmap", data, progressive: 0, animationDuration: 1500 }] });
  chart("regChart").setOption({ ...BASE, grid: { left: 46, right: 46, top: 34, bottom: 60 }, legend: LEG,
    tooltip: { ...BASE.tooltip, trigger: "axis" },
    xAxis: { type: "category", data: tk, ...AX, axisLabel: { color: C.muted, rotate: 70, fontSize: 10, fontFamily: "JetBrains Mono" } },
    yAxis: [{ type: "value", name: "% vốn / lô", ...AX }, { type: "value", name: "xác suất", min: 0, max: 1, ...AX, splitLine: { show: false } }],
    series: [{ name: "Giá 1 lô (% vốn)", type: "bar", data: d.register.map((r) => r.lot_pct), itemStyle: { color: C.q, borderRadius: [4, 4, 0, 0] } },
      { name: "Nới lỏng: nên mua?", type: "line", yAxisIndex: 1, data: d.register.map((r) => r.relaxed), symbolSize: 8, lineStyle: { color: C.accent }, itemStyle: { color: C.accent } }] });
}

/* ---------------- 4. AI design ---------------- */
function renderAI(d) {
  const a = d.ai, names = a.feature_names.map((f) => FEAT_VI[f] || f);
  const nb = a.neighbours.map((n) => n.z);
  const lo = names.map((_, i) => Math.min(...nb.map((z) => z[i]))), hi = names.map((_, i) => Math.max(...nb.map((z) => z[i])));
  chart("featChart").setOption({ ...BASE, grid: { left: 160, right: 30, top: 30, bottom: 30 }, legend: LEG,
    tooltip: { ...BASE.tooltip, trigger: "axis" },
    xAxis: { type: "value", name: "độ lệch chuẩn", ...AX }, yAxis: { type: "category", data: names, ...AX, axisLabel: { color: C.text } },
    series: [{ name: "khoảng của 10 láng giềng", type: "bar", stack: "r", data: lo, itemStyle: { color: "transparent" }, tooltip: { show: false } },
      { name: "10 bài toán 2023 giống nhất", type: "bar", stack: "r", data: hi.map((h, i) => +(h - lo[i]).toFixed(3)), itemStyle: { color: "rgba(56,189,248,.25)", borderRadius: 4 }, barWidth: 14 },
      { name: "bài toán hôm nay", type: "scatter", data: a.features_z, symbolSize: 16, itemStyle: { color: C.accent, borderColor: "#000" } }] });
  const s = a.schedule;
  $("#schedBox").innerHTML = `<div class="sched">
    <div><b>${s.layers}</b><small>số lớp p</small></div><div><b>${s.epsilon}</b><small>ε khởi động ấm</small></div>
    <div><b>${fmt(100 * s.coupling_mass, 0)}%</b><small>khối lượng J giữ lại</small></div><div><b>${s.dgamma}</b><small>Δγ dốc</small></div><div><b>${s.dbeta}</b><small>Δβ dốc</small></div></div>
    <div class="nbrs">Mô hình k-NN (k = ${a.k}, chọn bằng kiểm định chéo) tìm 10 bài toán năm 2023 giống nhất rồi chọn lịch tốt nhất trên chúng, trong ${vnd(a.schedules_considered)} lịch đã chấm điểm. ` +
    `Láng giềng: ${a.neighbours.slice(0, 6).map((n) => `${n.date.slice(0, 7)} (${fmt(n.capital_vnd / 1e6, 0)}tr)`).join(", ")}…${a.polish ? " Sau đó tinh chỉnh ngắn bằng COBYLA trên CVaR." : ""}</div>`;
  $("#rules").innerHTML = [
    `R1 · Khởi động ấm: mỗi qubit bắt đầu ở xác suất “nên mua” của nghiệm nới lỏng (kẹp trong [${s.epsilon}, ${1 - s.epsilon}]).`,
    `R2 · Bộ trộn căn chỉnh: trạng thái đầu là trạng thái riêng của bộ trộn.`,
    `R3 · Giữ ${d.hamiltonian.pairs_kept}/${d.hamiltonian.pairs_total} tương tác mạnh nhất (${fmt(100 * s.coupling_mass, 0)}% tổng J²).`,
    `R4 · Chia Hamiltonian cho RMS hệ số (${d.hamiltonian.scale.toExponential(2)}) để góc dùng lại được giữa các quý.`,
    `R5 · Góc dốc tuyến tính qua ${s.layers} lớp.`].map((t) => `<div>${t}</div>`).join("");
}

/* ---------------- 5. circuit SVG ---------------- */
function renderCircuit(d) {
  const n = d.register.length, p = d.circuit.layers, tk = d.register.map((r) => r.ticker);
  const rowH = 26, top = 46, left = 70, wInit = 70, wZZ = Math.min(260, 40 + d.hamiltonian.pairs_kept * 2.2), wRz = 46, wMix = 92, wMeas = 50;
  const layerW = wZZ + wRz + wMix + 24, W = left + wInit + p * layerW + wMeas + 30, H = top + n * rowH + 20;
  const y = (q) => top + q * rowH + rowH / 2;
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="font-family:JetBrains Mono">`;
  for (let q = 0; q < n; q++) {
    s += `<text x="${left - 8}" y="${y(q) + 4}" fill="${C.muted}" font-size="11" text-anchor="end">${tk[q]}</text>`;
    s += `<line class="draw" x1="${left}" y1="${y(q)}" x2="${W - 20}" y2="${y(q)}" stroke="#334155" stroke-width="1"/>`;
  }
  let x = left + 8, delay = 0.2;
  const box = (x0, w, label, color, sub) => `<g class="pop" style="animation-delay:${delay}s"><rect x="${x0}" y="${top - 2}" width="${w}" height="${n * rowH + 4}" rx="8" fill="${color}" fill-opacity=".08" stroke="${color}" stroke-opacity=".6"/>` +
    `<text x="${x0 + w / 2}" y="${top - 10}" fill="${color}" font-size="11" text-anchor="middle">${label}</text>${sub || ""}</g>`;
  // warm start
  let g = "";
  for (let q = 0; q < n; q++) g += `<rect x="${x + 10}" y="${y(q) - 9}" width="${wInit - 26}" height="18" rx="3" fill="${C.card}" stroke="${C.cl}"/><text x="${x + wInit / 2 - 3}" y="${y(q) + 4}" fill="${C.cl}" font-size="9.5" text-anchor="middle">Ry ${d.circuit.warm_theta[q].toFixed(2)}</text>`;
  s += box(x, wInit - 6, "khởi động ấm", C.cl, g); x += wInit; delay += 0.3;
  const kept = d.hamiltonian.kept, mxw = Math.max(...kept.map((k) => Math.abs(k.w))) || 1;
  for (let l = 0; l < p; l++) {
    // ZZ block: one vertical link per kept coupling
    let zz = ""; const step = (wZZ - 20) / Math.max(1, kept.length);
    kept.forEach((k, i) => { const xx = x + 10 + i * step, op = 0.25 + 0.75 * Math.abs(k.w) / mxw, col = k.w > 0 ? C.down : "#3b82f6";
      zz += `<line x1="${xx}" y1="${y(k.a)}" x2="${xx}" y2="${y(k.b)}" stroke="${col}" stroke-opacity="${op}" stroke-width="1.2"/><circle cx="${xx}" cy="${y(k.a)}" r="2.2" fill="${col}" fill-opacity="${op}"/><circle cx="${xx}" cy="${y(k.b)}" r="2.2" fill="${col}" fill-opacity="${op}"/>`; });
    s += box(x, wZZ, `ZZ(γ${l + 1}=${d.circuit.gammas[l].toFixed(2)})`, C.q, zz); x += wZZ + 4; delay += 0.25;
    let rz = ""; for (let q = 0; q < n; q++) rz += `<rect x="${x + 6}" y="${y(q) - 8}" width="${wRz - 12}" height="16" rx="3" fill="${C.card}" stroke="${C.q}"/><text x="${x + wRz / 2}" y="${y(q) + 4}" fill="${C.q}" font-size="9" text-anchor="middle">Rz</text>`;
    s += box(x, wRz, "h", C.q, rz); x += wRz + 4; delay += 0.2;
    let mx = ""; for (let q = 0; q < n; q++) mx += `<rect x="${x + 6}" y="${y(q) - 8}" width="${wMix - 12}" height="16" rx="3" fill="${C.card}" stroke="${C.ai}"/><text x="${x + wMix / 2}" y="${y(q) + 4}" fill="${C.ai}" font-size="9" text-anchor="middle">Ry·Rz(2β)·Ry</text>`;
    s += box(x, wMix, `trộn β${l + 1}=${d.circuit.betas[l].toFixed(2)}`, C.ai, mx); x += wMix + 16; delay += 0.25;
  }
  let me = ""; for (let q = 0; q < n; q++) me += `<rect x="${x + 6}" y="${y(q) - 9}" width="30" height="18" rx="3" fill="${C.card}" stroke="${C.accent}"/><path d="M${x + 11} ${y(q) + 5} Q${x + 21} ${y(q) - 8} ${x + 31} ${y(q) + 5}" stroke="${C.accent}" fill="none"/><line x1="${x + 21}" y1="${y(q) + 5}" x2="${x + 29}" y2="${y(q) - 6}" stroke="${C.accent}"/>`;
  s += box(x, wMeas - 6, "đo ×512", C.accent, me);
  $("#circuit").innerHTML = s + "</svg>";
  $("#circCaption").innerHTML = `Hình. Mạch QAOA ${n} qubit, p = ${p} lớp, ${d.hamiltonian.pairs_kept} cặp tương tác ZZ (đỏ: hai mã thay thế nhau; xanh: bổ sung nhau; đậm = mạnh), ${vnd(d.circuit.two_qubit_gates)} cổng hai qubit logic. Mỗi dòng là một qubit: “mua thêm 1 lô mã này?”.`;
  chart("rampChart").setOption({ ...BASE, grid: { left: 40, right: 20, top: 30, bottom: 30 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis" },
    xAxis: { type: "category", data: d.circuit.gammas.map((_, i) => "lớp " + (i + 1)), ...AX }, yAxis: { type: "value", ...AX },
    series: [{ name: "γ (bài toán)", type: "line", data: d.circuit.gammas, lineStyle: { color: C.q, width: 3 }, itemStyle: { color: C.q }, areaStyle: { color: "rgba(167,139,250,.12)" } },
      { name: "β (bộ trộn)", type: "line", data: d.circuit.betas, lineStyle: { color: C.ai, width: 3 }, itemStyle: { color: C.ai } }] });
  $("#circKpis").innerHTML = [[d.circuit.qubits, "qubit"], [p, "lớp QAOA"], [vnd(d.circuit.two_qubit_gates), "cổng 2 qubit logic"], [d.circuit.evaluations, "lần mô phỏng (gồm tinh chỉnh)"]]
    .map(([v, l]) => `<div class="k"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
}

/* ---------------- 6. sampling + verification ---------------- */
function renderSampling(d) {
  const r = d.result, arms = Object.keys(r.masses).sort((a, b) => (a === "AGQO") - (b === "AGQO")), bins = Object.keys(BIN_VI);
  chart("massChart").setOption({ ...BASE, grid: { left: 150, right: 20, top: 50, bottom: 30 }, legend: { ...LEG, itemWidth: 12 },
    tooltip: { ...BASE.tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => fmt(v, 1) + "%" },
    xAxis: { type: "value", max: 100, name: "% xác suất", ...AX }, yAxis: { type: "category", data: arms.map((a) => ARM_VI[a]), ...AX, axisLabel: { color: C.text } },
    series: bins.map((b) => ({ name: BIN_VI[b], type: "bar", stack: "m", data: arms.map((a) => +(100 * r.masses[a][b]).toFixed(2)), itemStyle: { color: BIN_COLOR[b] }, barWidth: 26 })) });
  $("#topStates").innerHTML = `<div class="states">` + r.top_states.map((t) => {
    const mx = r.top_states[0].prob;
    return `<div class="s"><div class="bits">${[...t.bits].map((b) => `<i class="${b === "1" ? "on" : ""}"></i>`).join("")}</div>` +
      `<div><div class="pbar" style="width:${(100 * t.prob / mx).toFixed(0)}%"></div></div><span>${fmt(100 * t.prob, 2)}%</span>` +
      `<span style="color:${t.optimal ? C.accent : t.gap_pct == null ? C.down : C.muted}">${t.optimal ? "★ tối ưu" : t.gap_pct == null ? "vượt vốn" : "+" + fmt(t.gap_pct, 1) + "%"}</span></div>`;
  }).join("") + `</div>`;
  const ratio = r.warm_success_pct > 0 ? r.success_pct / r.warm_success_pct : null;
  $("#verdict").innerHTML = `Trong ${vnd(r.states_total)} tổ hợp lô (${vnd(r.states_affordable)} đủ tiền), <b>${fmt(r.success_pct, 1)}%</b> lượt đo của mạch AGQO rơi vào nghiệm gần tối ưu, ` +
    `so với ${fmt(r.warm_success_pct, 1)}% của khởi động cổ điển${ratio ? ` (<b class="up">${fmt(ratio, 1)}×</b>)` : ""}, ${r.textbook_success_pct != null ? fmt(r.textbook_success_pct, 1) + "% của QAOA sách giáo khoa, " : ""}${fmt(r.random_success_pct, 2)}% nếu đoán ngẫu nhiên. ` +
    `Liệt kê cổ điển toàn bộ 2<sup>${d.register.length}</sup> tổ hợp trong ${fmt(d.seconds.enumerate_all, 2)} giây xác nhận: lựa chọn tốt nhất trong 512 lượt đo ` +
    (r.found_exact_optimum ? `<b class="up">chính là tối ưu chính xác</b>.` : `cách tối ưu ${fmt(r.best_sample_gap_pct, 2)}%.`);
}

/* ---------------- 7. portfolio + trades ---------------- */
function renderPortfolio(d) {
  const names = Object.keys(d.portfolios);
  chart("teBars").setOption({ ...BASE, grid: { left: 190, right: 60, top: 10, bottom: 20 }, tooltip: { ...BASE.tooltip },
    xAxis: { type: "value", name: "% / năm", ...AX }, yAxis: { type: "category", data: names.map((n) => PORT_VI[n]), inverse: true, ...AX, axisLabel: { color: C.text } },
    series: [{ type: "bar", data: names.map((n) => ({ value: d.portfolios[n].te_pct, itemStyle: { color: PORT_COLOR[n], borderRadius: [0, 6, 6, 0] } })), barWidth: 22,
      label: { show: true, position: "right", color: C.text, formatter: (p) => fmt(p.value, 2) + "%" } }] });
  const order = d.tickers.map((t, i) => i).sort((a, b) => d.portfolios["ideal (fractional shares)"].weights[b] - d.portfolios["ideal (fractional shares)"].weights[a]);
  chart("wChart").setOption({ ...BASE, grid: { left: 50, right: 20, top: 40, bottom: 60 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis", valueFormatter: (v) => fmt(v, 1) + "%" },
    xAxis: { type: "category", data: order.map((i) => d.tickers[i]), ...AX, axisLabel: { color: C.muted, rotate: 60, fontSize: 11, fontFamily: "JetBrains Mono" } },
    yAxis: { type: "value", name: "% vốn", ...AX },
    series: names.map((n) => ({ name: PORT_VI[n], type: "bar", data: order.map((i) => +(100 * d.portfolios[n].weights[i]).toFixed(2)), itemStyle: { color: PORT_COLOR[n] }, barGap: "8%" })) });
  $("#trades").innerHTML = `<tr><th>Mã</th><th>Ngành</th><th>Số lô</th><th>Giá</th><th>Giá trị</th></tr>` +
    d.trades.map((t) => `<tr><td><b>${t.ticker}</b></td><td>${SECTOR_VI[t.sector] || t.sector}</td><td>${t.lots}</td><td>${vnd(t.price_vnd)}</td><td>${vnd(t.value_vnd)}</td></tr>`).join("") +
    `<tr><td colspan="4">Phí giao dịch</td><td>${vnd(d.fees_vnd)}</td></tr><tr><td colspan="4"><b>Tiền mặt còn lại</b></td><td><b>${vnd(d.cash_after_vnd)}</b></td></tr>`;
  const ag = d.portfolios.AGQO;
  $("#checks").innerHTML = [`Tổng đầu tư ${fmt(ag.invested_pct)}% · ${ag.holdings} mã`, ...d.checks.map((c) => c.rule.replace("invested share", "Tỷ trọng đầu tư").replace("no excluded stock or sector held", "Không giữ mã/ngành bị loại").replace("cash never negative after fees", "Đủ tiền sau phí").replace(/^at most (\d+) stocks$/, "Tối đa $1 mã") + (c.value_pct != null ? ` (thực tế ${fmt(c.value_pct)}%)` : ""))]
    .map((t, i) => `<li class="${i > 0 && !d.checks[i - 1].ok ? "bad" : ""}">${t}</li>`).join("") +
    `<li>Đã đối chiếu với tối ưu chính xác của toàn bộ 2<sup>16</sup> tổ hợp</li>`;
  $("#qasmBtn").href = `/api/qasm/${d.id}`;
  $("#explain").innerHTML = "";
}

/* ---------------- LLM jobs ---------------- */
async function pollJob(id, onTick) {
  for (;;) {
    await sleep(4000);
    const r = await api(`/api/job/${id}`);
    if (r.status !== "running") return r;
    onTick(r.seconds);
  }
}
function highlightNumbers(text, bad) {
  const badSet = new Set(bad || []);
  return text.replace(/\d+(?:[.,]\d+)*/g, (m) => { const norm = m.replace(/\./g, "").replace(",", "."); return `<mark class="${badSet.has(norm) || badSet.has(m) ? "bad" : ""}">${m}</mark>`; });
}
async function explain() {
  if (!LAST) return;
  const box = $("#explain");
  box.innerHTML = `<div class="explain"><span class="spinner"></span>Đang gửi bằng chứng do mã nguồn tạo cho Qwen3.8-27B…</div>`;
  try {
    const r = await api("/api/explain", { id: LAST.id });
    if (!r.job) { box.innerHTML = `<div class="explain">${r.note}. Bằng chứng LLM sẽ nhận:<pre class="code">${JSON.stringify(r.evidence, null, 1)}</pre></div>`; return; }
    const res = await pollJob(r.job, (s) => box.innerHTML = `<div class="explain"><span class="spinner"></span>Qwen3.8 đang viết giải thích (${s} giây${s > 20 ? "; GPU đang khởi động, lần đầu mất khoảng 6 phút" : ""})…</div>`);
    if (res.status !== "done" || !res.explanation) { box.innerHTML = `<div class="explain">Không nhận được giải thích (${res.error || "lỗi"}).</div>`; return; }
    const e = res.explanation, ck = res.check, bad = ck.unverified_numbers;
    box.innerHTML = `<div class="explain"><p>${highlightNumbers(e.summary_vi, bad)}</p>` +
      (e.trade_notes || []).map((t) => `<p>• <b>${t.ticker}</b> ${t.action} ${t.lots} lô: ${highlightNumbers(t.reason_vi, bad)}</p>`).join("") +
      (e.risk_notes_vi || []).map((t) => `<p>⚠ ${highlightNumbers(t, bad)}</p>`).join("") +
      `<p class="muted">Kiểm tra tự động: ${ck.ok ? `<b class="up">mọi con số và lệnh khớp với bằng chứng</b>` : `<b class="down">${bad.length} số không có trong bằng chứng, ${ck.trade_mismatches.length} lệnh lệch, ${ck.context_issues.length} lỗi ngữ cảnh</b>`} · ${res.usage?.input_tokens || "?"} token vào, ${res.usage?.output_tokens || "?"} token ra · ${res.gpu || ""}</p></div>`;
  } catch (err) { box.innerHTML = `<div class="explain">Lỗi: ${err.message}</div>`; }
}

/* ---------------- run the pipeline ---------------- */
async function run() {
  const btn = $("#runBtn"); btn.disabled = true; btn.textContent = "Đang chạy…";
  $("#out").classList.remove("hidden"); document.querySelectorAll(".panel").forEach((p) => p.classList.remove("show"));
  $("#llmLive").innerHTML = "";
  const capital = Math.max(5, Math.min(2000, +$("#capital").value || 20));
  try {
    stepTo(1);
    const mres = await api("/api/mandate", { text: $("#instr").value, live: $("#liveLLM").checked });
    renderMandate(mres); await showPanel(1);
    await decideAndShow(capital, mres.mandate);
    if (mres.job) liveMandate(mres.job, capital, mres.mandate);
  } catch (err) { toast("Lỗi: " + err.message, 7000); }
  btn.disabled = false; btn.textContent = "▶ Chạy AGQO";
}
async function decideAndShow(capital, mandate) {
  stepTo(2);
  const d = await api("/api/decide", { capital_million: capital, mandate });
  LAST = d;
  renderMarket(d); await showPanel(2);
  renderHamiltonian(d); await showPanel(3);
  renderAI(d); await showPanel(4);
  renderCircuit(d); await showPanel(5);
  renderSampling(d); await showPanel(6);
  renderPortfolio(d); await showPanel(7);
  stepTo(8);
  Object.values(charts).forEach((c) => c.resize());
}
async function liveMandate(job, capital, shown) {
  const box = $("#llmLive");
  box.innerHTML = `<div class="bubble"><span class="spinner"></span>Đang chạy bằng quy tắc từ khóa; Qwen3.8 đang đọc yêu cầu trên GPU H100…</div>`;
  const res = await pollJob(job, (s) => box.innerHTML = `<div class="bubble"><span class="spinner"></span>Qwen3.8 đang đọc yêu cầu (${s} giây${s > 20 ? "; GPU khởi động lần đầu mất khoảng 6 phút, kết quả sẽ tự cập nhật" : ""})…</div>`);
  if (res.status !== "done") { box.innerHTML = `<div class="bubble">LLM không phản hồi (${res.error || "lỗi"}); giữ kết quả theo quy tắc từ khóa.</div>`; return; }
  renderMandate(res);
  const same = JSON.stringify(res.mandate) === JSON.stringify(shown);
  box.innerHTML = `<div class="bubble">✔ Qwen3.8 trả lời sau ${res.seconds} giây. ${same ? "Ràng buộc trùng với quy tắc từ khóa." : "Ràng buộc khác quy tắc từ khóa: chạy lại AGQO với ràng buộc của LLM."}</div>`;
  if (!same && !res.needs_clarification) { toast("Qwen3.8 đã dịch xong yêu cầu, đang chạy lại AGQO"); await decideAndShow(capital, res.mandate); }
}

/* ---------------- results section ---------------- */
async function story() {
  const s = await api("/api/story");
  const st = s.stats;
  $("#statKpis").innerHTML = [[st["agqo vs warm_start_only"], "so với khởi động ấm cổ điển"], [st["agqo vs textbook"], "so với QAOA sách giáo khoa"], [st["agqo vs random"], "so với tìm kiếm ngẫu nhiên"]]
    .map(([x, l]) => `<div class="k"><div class="v up">${fmt(x.ratio)}×</div><div class="l">${l} · thắng ${x.wins}/${x.n} quý · p = ${fmt(x.wilcoxon_p, 4)}</div></div>`).join("") +
    `<div class="k"><div class="v">${fmt(100 * st["agqo vs warm_start_only"].mean_a)}%</div><div class="l">lượt đo trúng nghiệm gần tối ưu (trung bình 12 quý)</div></div>`;
  const qcol = { "AGQO": C.ai, "Khởi động ấm (cổ điển)": C.cl, "QAOA sách giáo khoa": C.q, "Tìm kiếm ngẫu nhiên": C.amber };
  chart("qChart").setOption({ ...BASE, grid: { left: 50, right: 20, top: 40, bottom: 40 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis", valueFormatter: (v) => fmt(v, 1) + "%" },
    xAxis: { type: "category", data: s.quarters.dates.map((d) => d.slice(0, 7)), ...AX }, yAxis: { type: "value", name: "% lượt đo", ...AX },
    series: Object.entries(s.quarters.series).map(([k, v]) => ({ name: k, type: k === "AGQO" ? "bar" : "line", data: v, smooth: true, symbolSize: 7,
      itemStyle: { color: qcol[k], borderRadius: [5, 5, 0, 0] }, lineStyle: { color: qcol[k], width: 2.5 } })) });
  const acc = s.accounts;
  chart("accChart").setOption({ ...BASE, grid: { left: 50, right: 20, top: 64, bottom: 30 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis", valueFormatter: (v) => fmt(v, 1) + "%" },
    xAxis: { type: "category", data: acc.map((a) => fmt(a.capital_vnd / 1e6, 0) + " triệu"), ...AX }, yAxis: { type: "value", name: "sai số bám %/năm", ...AX },
    series: [["Làm tròn lô gần nhất", "te_practitioner", C.down], ["Tham lam", "te_greedy", C.amber], ["AGQO", "te_whole_lot_optimum", C.ai]].map(([n, k, c]) => ({ name: n, type: "bar", data: acc.map((a) => +a[k].toFixed(2)), itemStyle: { color: c, borderRadius: [5, 5, 0, 0] }, label: { show: true, position: "top", color: C.text, formatter: (p) => fmt(p.value, 1) } })) });
  const bcol = { "AGQO": C.ai, "Làm tròn lô gần nhất": C.down, "Chỉ số VN30": C.accent, "ETF E1VFVN30": C.grey };
  chart("btChart").setOption({ ...BASE, grid: { left: 50, right: 20, top: 64, bottom: 30 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis", valueFormatter: (v) => fmt(v, 1) + " tr" },
    xAxis: { type: "category", data: s.backtest.dates, ...AX }, yAxis: { type: "value", name: "triệu đồng", scale: true, ...AX },
    series: Object.entries(s.backtest.series).map(([k, v]) => ({ name: k, type: "line", data: v, showSymbol: false, lineStyle: { width: k === "AGQO" ? 2.6 : 1.4, color: bcol[k] }, itemStyle: { color: bcol[k] } })) });
  const by = {}; s.scaling.forEach((r) => { (by[r.qubits] ||= { w: [], f: [] }); by[r.qubits].w.push(r.warm_success); by[r.qubits].f.push(r.frozen_success); });
  const qs = Object.keys(by).sort((a, b) => a - b), mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  chart("scChart").setOption({ ...BASE, grid: { left: 50, right: 50, top: 40, bottom: 30 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis" },
    xAxis: { type: "category", data: qs.map((q) => q + " qubit"), ...AX }, yAxis: [{ type: "value", name: "% lượt đo", ...AX }, { type: "value", name: "lần", ...AX, splitLine: { show: false } }],
    series: [{ name: "Mạch AGQO", type: "bar", data: qs.map((q) => +(100 * mean(by[q].f)).toFixed(2)), itemStyle: { color: C.ai, borderRadius: [5, 5, 0, 0] } },
      { name: "Khởi động ấm", type: "bar", data: qs.map((q) => +(100 * mean(by[q].w)).toFixed(2)), itemStyle: { color: C.cl, borderRadius: [5, 5, 0, 0] } },
      { name: "Gấp (lần)", type: "line", yAxisIndex: 1, data: qs.map((q) => +(mean(by[q].f) / mean(by[q].w)).toFixed(1)), lineStyle: { color: C.accent, width: 3 }, itemStyle: { color: C.accent }, symbolSize: 10, label: { show: true, color: C.accent, formatter: (p) => p.value + "×" } }] });
  $("#manTable").innerHTML = `<table class="tbl"><tr><th>Yêu cầu (tiếng Việt)</th><th>Sai số bám</th><th>Chi phí quy tắc</th><th>Vi phạm</th></tr>` +
    s.mandates.map((m) => `<tr><td>${m.instruction === "(none)" ? "<i>(không có yêu cầu)</i>" : m.instruction}</td><td>${fmt(m.tracking_error_ann_pct, 2)}%</td><td>+${fmt(m.te_cost_vs_unconstrained_pp, 2)} đ%</td><td class="up"><b>${m.rule_violations_at_rebalance}</b></td></tr>`).join("") + `</table>`;
}

/* ---------------- boot ---------------- */
(async function boot() {
  try {
    META = await api("/api/meta");
    $("#asof").textContent = `Dữ liệu đến ${META.date} · ${META.universe.length} mã VN30`;
    const tape = META.stocks.map((s) => `<span><b>${s.ticker}</b>1 lô ${vnd(s.lot_vnd)} đ <span class="${s.lot_vnd > 2e6 ? "down" : "up"}">${fmt(100 * s.lot_vnd / 20e6)}% của 20tr</span></span>`).join("");
    $("#tape").innerHTML = tape + tape;
    const pick = ["Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này", "Ngân hàng tối đa 30%", "Tôi không thích rủi ro, hãy để 10% tiền mặt và mỗi cổ phiếu tối đa 8%",
      "Không đầu tư bất động sản, ngân hàng tối đa 30%", "Tôi muốn tập trung, chỉ 8 mã thôi", "Tôi muốn ít rủi ro hơn"].filter((e) => META.examples.includes(e) || e === "Tôi muốn ít rủi ro hơn");
    $("#examples").innerHTML = `<span class="muted" style="margin:0 6px 0 0">Ví dụ (đã chạy thật với Qwen3.8):</span>` + pick.map((e) => `<span class="chip">${e}</span>`).join("");
    document.querySelectorAll("#examples .chip").forEach((c) => c.onclick = () => { $("#instr").value = c.textContent; });
    if (!META.live_llm) { $("#liveLLM").checked = false; $("#liveLLM").disabled = true; }
    lotChart(20);
    $("#capSlider").oninput = (e) => { $("#capLabel").textContent = e.target.value; lotChart(+e.target.value); };
    $("#runBtn").onclick = run; $("#explainBtn").onclick = explain;
    await story();
    // shareable link that runs a decision on load: /?run=1&capital=20&q=Ngân hàng tối đa 30%&live=0
    const P = new URLSearchParams(location.search);
    if (P.get("capital")) $("#capital").value = P.get("capital");
    if (P.get("q")) $("#instr").value = P.get("q");
    if (P.get("live") === "0") $("#liveLLM").checked = false;
    if (P.get("run") === "1") { document.documentElement.style.scrollBehavior = "auto"; $("#try").scrollIntoView(); await run(); document.body.dataset.done = "1"; }
  } catch (err) { toast("Không tải được dữ liệu: " + err.message, 8000); }
})();
