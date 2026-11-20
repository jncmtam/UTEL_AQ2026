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
let META = null;

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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
    series: [{ name: `khoảng của ${nb.length} láng giềng`, type: "bar", stack: "r", data: lo, itemStyle: { color: "transparent" }, tooltip: { show: false } },
      { name: `${nb.length} bài toán 2023 giống nhất`, type: "bar", stack: "r", data: hi.map((h, i) => +(h - lo[i]).toFixed(3)), itemStyle: { color: "rgba(56,189,248,.25)", borderRadius: 4 }, barWidth: 14 },
      { name: "bài toán hôm nay", type: "scatter", data: a.features_z, symbolSize: 16, itemStyle: { color: C.accent, borderColor: "#000" } }] });
  const s = a.schedule;
  $("#schedBox").innerHTML = `<div class="sched">
    <div><b>${s.layers}</b><small>số lớp p</small></div><div><b>${s.epsilon}</b><small>ε khởi động ấm</small></div>
    <div><b>${fmt(100 * s.coupling_mass, 0)}%</b><small>khối lượng J giữ lại</small></div><div><b>${s.dgamma}</b><small>Δγ dốc</small></div><div><b>${s.dbeta}</b><small>Δβ dốc</small></div></div>
    <div class="nbrs">Mô hình k-NN (k = ${a.k}, chọn bằng kiểm định chéo) tìm ${a.neighbours.length} bài toán năm 2023 giống nhất rồi chọn lịch tốt nhất trên chúng, trong ${vnd(a.schedules_considered)} lịch đã chấm điểm. ` +
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

/* ================= V3.2: structured constraints, presets, Modal jobs ================= */
const FIELDS = ["capital", "exclude_sectors", "exclude_tickers", "sector_caps", "max_weight_per_stock", "max_holdings", "min_cash_pct"];
const SRC_VI = { user: "Bạn nhập", preset: "Từ mẫu", text: "Từ câu lệnh", unset: "Chưa đặt" };
const DEFAULT_VI = { exclude_sectors: "không loại ngành nào", exclude_tickers: "không loại mã nào", sector_caps: "không có trần ngành",
  max_weight_per_stock: "không giới hạn", max_holdings: "giữ bao nhiêu mã cũng được", min_cash_pct: "không đặt; giữ khoảng 2% làm đệm phí" };
const STAGE_VI = { queued: "Đang xếp hàng trên Modal", started: "Container Modal đã khởi động", load: "Nạp dữ liệu VN30 và mô hình",
  feasibility: "Kiểm tra yêu cầu có khả thi không", build_qubo: "Dựng bài toán chọn lô (QUBO)", enumerate: "Liệt kê toàn bộ tổ hợp lô để kiểm chứng",
  baselines: "Tính các cách cổ điển để so sánh", schedule: "AI (k-NN) chọn lịch cho mạch", qaoa: "Mô phỏng mạch QAOA, đo 512 lần",
  textbook: "Chạy QAOA sách giáo khoa để so sánh", verify: "Kiểm tra mọi quy tắc trên NAV sau phí", evidence: "Chuẩn bị bằng chứng cho lời giải thích",
  done: "Xong" };
const STAGES = ["queued", "started", "load", "feasibility", "build_qubo", "enumerate", "baselines", "schedule", "qaoa", "textbook", "verify", "evidence", "done"];
let FORM = { capital: 20, exclude_sectors: [], exclude_tickers: [], sector_caps: {}, max_weight_per_stock: null, max_holdings: null, min_cash_pct: null };
let SRC = Object.fromEntries(FIELDS.map((f) => [f, f === "capital" ? "user" : "unset"]));
let PRESET = null, PENDING = null, LAST_RUN = null, LAST_BODY = null;

function isSet(f, v) { return Array.isArray(v) ? v.length > 0 : (v && typeof v === "object") ? Object.keys(v).length > 0 : v != null && v !== ""; }
function mandateOf() {
  return { exclude_tickers: FORM.exclude_tickers, exclude_sectors: FORM.exclude_sectors, sector_caps: FORM.sector_caps,
    max_weight_per_stock: FORM.max_weight_per_stock, max_holdings: FORM.max_holdings, min_cash_pct: FORM.min_cash_pct };
}
function applyMandate(m, src, capital) {
  FORM = { capital: capital ?? FORM.capital, exclude_sectors: [...(m.exclude_sectors || [])], exclude_tickers: [...(m.exclude_tickers || [])],
    sector_caps: { ...(m.sector_caps || {}) }, max_weight_per_stock: m.max_weight_per_stock ?? null, max_holdings: m.max_holdings ?? null, min_cash_pct: m.min_cash_pct ?? null };
  for (const f of FIELDS) if (f !== "capital") SRC[f] = isSet(f, FORM[f]) ? src : "unset";
  if (capital != null) SRC.capital = src;
  renderForm();
}
function touch(f) { SRC[f] = isSet(f, FORM[f]) || f === "capital" ? "user" : "unset"; PRESET = null; markPreset(); renderSrc(); validateForm(); }
function renderSrc() {
  for (const f of FIELDS) {
    const el = $(`#src-${f}`); if (!el) continue;
    el.className = `src ${SRC[f]}`;
    el.textContent = SRC[f] === "unset" ? `Chưa đặt · ${DEFAULT_VI[f]}` : SRC_VI[SRC[f]];
  }
}
function renderForm() {
  $("#capital").value = FORM.capital;
  $("#maxW").value = FORM.max_weight_per_stock != null ? +(100 * FORM.max_weight_per_stock).toFixed(2) : "";
  $("#maxH").value = FORM.max_holdings ?? "";
  $("#minCash").value = FORM.min_cash_pct ?? "";
  $("#secChips").innerHTML = META.sectors.map((s) => `<span class="chip tog ${FORM.exclude_sectors.includes(s.en) ? "on" : ""}" data-s="${s.en}">${s.vi}</span>`).join("");
  document.querySelectorAll("#secChips .chip").forEach((c) => c.onclick = () => {
    const s = c.dataset.s; FORM.exclude_sectors = FORM.exclude_sectors.includes(s) ? FORM.exclude_sectors.filter((x) => x !== s) : [...FORM.exclude_sectors, s].sort();
    c.classList.toggle("on"); touch("exclude_sectors"); });
  $("#tickChips").innerHTML = FORM.exclude_tickers.map((t) => `<span class="chip rm" data-t="${t}">${t} ✕</span>`).join("");
  document.querySelectorAll("#tickChips .chip").forEach((c) => c.onclick = () => { FORM.exclude_tickers = FORM.exclude_tickers.filter((x) => x !== c.dataset.t); renderForm(); touch("exclude_tickers"); });
  $("#caps").innerHTML = Object.entries(FORM.sector_caps).map(([s, v]) => `<div class="cap-row" data-s="${s}"><select>${META.sectors.map((x) => `<option value="${x.en}" ${x.en === s ? "selected" : ""}>${x.vi}</option>`).join("")}</select>` +
    `<span>tối đa</span><input type="number" min="0.5" max="100" step="0.5" value="${+(100 * v).toFixed(2)}"><span>%</span><button class="btn tiny ghost" type="button">✕</button></div>`).join("");
  document.querySelectorAll("#caps .cap-row").forEach((row) => {
    const old = row.dataset.s, sel = row.querySelector("select"), inp = row.querySelector("input");
    const upd = () => { const caps = { ...FORM.sector_caps }; delete caps[old]; const v = parseFloat(inp.value); if (isFinite(v)) caps[sel.value] = v / 100; FORM.sector_caps = caps; renderForm(); touch("sector_caps"); };
    sel.onchange = upd; inp.onchange = upd;
    row.querySelector("button").onclick = () => { const caps = { ...FORM.sector_caps }; delete caps[old]; FORM.sector_caps = caps; renderForm(); touch("sector_caps"); };
  });
  renderSrc(); validateForm();
}
function validateForm() {
  const errs = [];
  if (!(FORM.capital >= 5 && FORM.capital <= 2000)) errs.push("Số vốn phải từ 5 đến 2.000 triệu đồng.");
  if (FORM.max_weight_per_stock != null && !(FORM.max_weight_per_stock > 0 && FORM.max_weight_per_stock <= 1)) errs.push("“Mỗi mã tối đa” phải trong (0, 100]%.");
  if (FORM.max_holdings != null && !(Number.isInteger(FORM.max_holdings) && FORM.max_holdings >= 1 && FORM.max_holdings <= 30)) errs.push("“Tối đa số mã” là số nguyên từ 1 đến 30.");
  if (FORM.min_cash_pct != null && !(FORM.min_cash_pct >= 0 && FORM.min_cash_pct < 100)) errs.push("Tiền mặt tối thiểu phải trong [0, 100)%.");
  for (const [s, v] of Object.entries(FORM.sector_caps)) if (!(v > 0 && v <= 1)) errs.push(`Trần ngành ${SECTOR_VI[s] || s} phải trong (0, 100]%.`);
  for (const s of FORM.exclude_sectors) if (s in FORM.sector_caps) errs.push(`Ngành ${SECTOR_VI[s]} vừa bị loại vừa có trần: khi chạy, quy tắc loại được áp dụng.`);
  $("#formErr").innerHTML = errs.map((e) => `<div>${e}</div>`).join("");
  const blocking = errs.filter((e) => !e.includes("quy tắc loại được áp dụng")).length;
  $("#runBtn").disabled = !!PENDING || blocking > 0;
  $("#runNote").innerHTML = PENDING ? `<b class="amber">Hãy trả lời câu hỏi làm rõ ở bước 2</b> (hoặc chọn bỏ qua) trước khi chạy.` : "";
  return blocking === 0;
}
function bindForm() {
  const num = (id, f, scale = 1, int = false) => $(id).onchange = (e) => {
    const v = e.target.value === "" ? null : (int ? parseInt(e.target.value, 10) : parseFloat(e.target.value) / scale);
    FORM[f] = v; touch(f); };
  $("#capital").onchange = (e) => { FORM.capital = parseFloat(e.target.value); touch("capital"); };
  num("#maxW", "max_weight_per_stock", 100); num("#maxH", "max_holdings", 1, true); num("#minCash", "min_cash_pct");
  $("#tickList").innerHTML = Object.keys(SECTOR_OF).sort().map((t) => `<option value="${t}">${SECTOR_VI[SECTOR_OF[t]] || ""}</option>`).join("");
  $("#tickIn").onkeydown = (e) => { if (e.key !== "Enter") return; e.preventDefault();
    const t = e.target.value.trim().toUpperCase(); if (!SECTOR_OF[t]) { toast(`Không có mã ${t} trong dữ liệu VN30`); return; }
    if (!FORM.exclude_tickers.includes(t)) FORM.exclude_tickers = [...FORM.exclude_tickers, t].sort();
    e.target.value = ""; renderForm(); touch("exclude_tickers"); };
  $("#addCap").onclick = () => { const free = META.sectors.find((s) => !(s.en in FORM.sector_caps)); if (!free) return;
    FORM.sector_caps = { ...FORM.sector_caps, [free.en]: 0.3 }; renderForm(); touch("sector_caps"); };
  const f = META.fees;
  $("#feeNote").innerHTML = `Phí: mua ${fmt(f.commission_pct, 2)}% giá trị khớp; bán ${fmt(f.commission_pct, 2)}% + thuế ${fmt(f.sell_tax_pct, 1)}%. Lô = ${f.lot_size} cổ phiếu. ` +
    `Mọi giới hạn được kiểm tra trên <b>NAV sau phí</b> = tiền mặt còn lại sau khi trả phí + giá trị cổ phiếu vừa mua. Vì phí làm NAV nhỏ đi một chút, ` +
    `một danh mục “vừa đúng 25%” tính trên vốn ban đầu có thể vượt 25% sau phí; AGQO chừa sẵn biên cho phí để điều này không xảy ra.`;
}

/* ---------------- presets ---------------- */
const EXPECT_VI = { favourable: ["Có lợi", "up"], unfavourable: ["Ít lợi / đánh đổi", "amber"], "no clear difference": ["Không khác biệt rõ", "amber"],
  infeasible: ["Không khả thi", "down"], clarification: ["Cần hỏi lại", "ai"] };
function renderPresets() {
  $("#presets").innerHTML = META.presets.map((p) => {
    const m = p.measured || {}, cls_ = m.outcome || p.expect, [lab, cls] = EXPECT_VI[cls_] || EXPECT_VI[p.expect] || ["", ""];
    const meas = m.realised_te_agqo_pct != null ? `Đo trên Modal, 12 quý: sai số bám ${fmt(m.realised_te_agqo_pct, 2)}% (làm tròn: ${fmt(m.realised_te_rounding_pct, 2)}%)` +
        (m.rule_cost_pp ? ` · quy tắc làm tăng ${fmt(m.rule_cost_pp, 2)} điểm %` : "")
      : m.status === "infeasible" ? `Đo trên Modal: không khả thi` : m.status === "needs_clarification" ? "Đo: hệ thống hỏi lại, không hiện lệnh" : "";
    return `<div class="pcard" data-id="${p.id}"><div class="pt"><b>${p.title_vi}</b><span class="badge ${cls}">${lab}</span></div>` +
      `<p>${p.why_vi}</p><p class="muted">Đánh đổi: ${p.tradeoff_vi}</p>${meas ? `<p class="meas">${meas}</p>` : ""}</div>`;
  }).join("");
  document.querySelectorAll(".pcard").forEach((el) => el.onclick = () => choosePreset(el.dataset.id));
}
function markPreset() { document.querySelectorAll(".pcard").forEach((el) => el.classList.toggle("on", el.dataset.id === PRESET)); }
async function choosePreset(id) {
  const p = META.presets.find((x) => x.id === id);
  PENDING = null; $("#clarify").innerHTML = ""; $("#llmLive").innerHTML = ""; $("#mandateSource").innerHTML = "";
  applyMandate(p.mandate, "preset", p.capital_million);
  PRESET = id; markPreset();
  if (p.instruction_vi) { $("#instr").value = p.instruction_vi; await parseInstruction(); PRESET = id; markPreset(); }
  else $("#instr").value = "";
  $("#constraintCard").scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ---------------- instruction -> constraints ---------------- */
function showClarify(question, text, conflicts) {
  PENDING = { question, text };
  $("#clarify").innerHTML = `<div class="bubble ask">🤖 ${conflicts ? "Yêu cầu có mâu thuẫn" : "Cần làm rõ"}: “${question}”` +
    (conflicts?.length ? `<br><small class="muted">Mâu thuẫn phát hiện: ${conflicts.join("; ")}</small>` : "") + `<div class="ans"><input id="ansIn" placeholder="Trả lời, VD: tối đa 25%"><button class="btn tiny" id="ansBtn">Gửi trả lời</button>` +
    `<button class="btn tiny ghost" id="skipBtn">Bỏ qua, không đặt giới hạn này</button></div><small>Chưa có lệnh nào được tạo: AGQO chờ câu trả lời của bạn.</small></div>`;
  $("#ansBtn").onclick = async () => { const a = $("#ansIn").value.trim(); if (!a) return; $("#instr").value = `${text}. ${a}`; await parseInstruction(); };
  $("#ansIn").onkeydown = (e) => { if (e.key === "Enter") $("#ansBtn").click(); };
  $("#skipBtn").onclick = () => { PENDING = null; $("#clarify").innerHTML = `<div class="bubble">Bạn chọn chạy mà không đặt giới hạn cho câu “${text}”.</div>`; validateForm(); };
  validateForm();
}
function showMandateResult(res, text) {
  const live = res.source.includes("live") || res.source.includes("logged");
  $("#mandateSource").innerHTML = `Nguồn diễn giải: <b style="color:${live ? C.ai : C.amber}">${res.source}</b>${res.llm_note ? " · " + res.llm_note : ""}` +
    (res.errors?.length ? ` · <span class="down">câu trả lời bị loại: ${res.errors.join("; ")}</span>` : "");
  applyMandate(res.mandate, "text");
  if ((res.status === "needs_clarification" || res.status === "conflict") && res.question) showClarify(res.question, text, res.status === "conflict" ? res.conflicts : null);
  else { PENDING = null; $("#clarify").innerHTML = ""; validateForm(); }
}
async function parseInstruction() {
  const text = $("#instr").value.trim();
  $("#llmLive").innerHTML = "";
  if (!text) { toast("Hãy nhập yêu cầu hoặc chọn một mẫu."); return; }
  const btn = $("#parseBtn"); btn.disabled = true;
  try {
    const res = await api("/api/mandate", { text, live: $("#liveLLM").checked });
    PRESET = null; markPreset();
    showMandateResult(res, text);
    if (res.job) liveMandate(res.job, text);
  } catch (err) { toast("Lỗi diễn giải: " + err.message, 6000); }
  btn.disabled = false;
}
async function liveMandate(job, text) {
  const box = $("#llmLive");
  box.innerHTML = `<div class="bubble"><span class="spinner"></span>Đang hiện kết quả quy tắc từ khóa; Qwen3.8 đang đọc yêu cầu trên GPU H100…</div>`;
  const res = await pollJob(job, (s) => box.innerHTML = `<div class="bubble"><span class="spinner"></span>Qwen3.8 đang đọc yêu cầu (${s} giây${s > 20 ? "; GPU khởi động lần đầu mất khoảng 6 phút" : ""})…</div>`);
  if ($("#instr").value.trim() !== text) { box.innerHTML = ""; return; }           // the user moved on
  if (res.status !== "done") { box.innerHTML = `<div class="bubble">Qwen3.8 không phản hồi (${res.error || "lỗi"}); giữ kết quả quy tắc từ khóa.</div>`; return; }
  box.innerHTML = `<div class="bubble">✔ Qwen3.8 trả lời sau ${res.seconds} giây; các ô bên dưới đã cập nhật. Hãy xem lại rồi bấm Chạy.</div>`;
  showMandateResult(res, text);
}

/* ---------------- run on Modal ---------------- */
function jobBox(html) { const b = $("#job"); b.classList.remove("hidden"); b.innerHTML = html; }
function progressHtml(st) {
  const cur = st.stage?.stage || st.status, i = Math.max(0, STAGES.indexOf(cur));
  const pct = Math.round(100 * (i + 1) / STAGES.length);
  const where = st.mode === "live_modal" ? `job Modal <code>${st.function_call || ""}</code>${st.stage?.container ? ` · container <code>${st.stage.container}</code>` : ""}` : st.mode;
  return `<div class="jobrow"><span class="spinner"></span><b>${STAGE_VI[cur] || cur}</b><span class="muted">${fmt(st.seconds || 0, 0)} giây · ${where}</span></div>` +
    `<div class="bar"><i style="width:${pct}%"></i></div>` +
    (st.status === "queued" && (st.seconds || 0) > 8 ? `<small class="muted">Container đang khởi động (lần đầu có thể mất 20–60 giây).</small>` : "");
}
async function runJob(body) {
  LAST_BODY = body;
  const btn = $("#runBtn"); btn.disabled = true; btn.textContent = "Đang chạy…";
  $("#out").classList.add("hidden");
  jobBox(progressHtml({ status: "queued", mode: "live_modal", seconds: 0 }));
  try {
    const start = await api("/api/run", body);
    let st = start;
    const t0 = Date.now();
    while (st.status !== "done" && st.status !== "failed") {
      jobBox(progressHtml(st));
      await sleep(1000);
      st = await api(`/api/run/${start.id}`);
      if (Date.now() - t0 > 10 * 60 * 1000) throw new Error("job chạy quá 10 phút");
    }
    if (st.status === "failed") throw new Error(st.error || "job thất bại");
    if (start.status === "done" && !st.result) st = await api(`/api/run/${start.id}`);
    $("#job").classList.add("hidden");
    LAST_RUN = { id: start.id, ...st.result, sources: st.sources || body.sources };
    await showResult(LAST_RUN, st);
  } catch (err) {
    jobBox(`<div class="jobrow"><b class="down">Không hoàn tất: ${err.message}</b></div>` +
      `<p class="muted">Lỗi thường gặp: container Modal đang khởi động, mạng chập chờn, hoặc máy chủ web vừa khởi động lại. Bấm thử lại; ràng buộc của bạn vẫn giữ nguyên.</p>` +
      `<button class="btn" id="retryBtn">↻ Thử lại</button>`);
    $("#retryBtn").onclick = () => runJob(LAST_BODY);
  }
  btn.textContent = "▶ Chạy trên Modal"; validateForm();
}
function runClicked() {
  if (!validateForm()) return;
  runJob({ capital_million: FORM.capital, mandate: mandateOf(), sources: { ...SRC }, preset_id: PRESET, clarification_pending: !!PENDING });
}

/* ---------------- result ---------------- */
function execLabel(e) {
  if (!e) return "";
  if (e.mode === "live_modal") return `<span class="exec live">● Chạy thật trên Modal · container ${e.container || "?"} · ${fmt(e.seconds, 1)} giây</span>`;
  if (e.mode === "replay") return `<span class="exec replay">↺ Phát lại kết quả Modal đã lưu (run ${e.run_id}) · không tính lại${e.why ? " · lý do: " + e.why : ""}</span>`;
  return `<span class="exec fallback">⚠ Dự phòng: tính trong máy chủ web, không phải job Modal${e.why ? " · " + e.why : ""}</span>`;
}
function checkLabel(c) {
  const v = (x) => fmt(x, 2) + "%";
  switch (c.kind) {
    case "sector_cap": return `Ngành ${SECTOR_VI[c.sector] || c.sector} ≤ ${fmt(c.limit_pct, 1)}% · thực tế ${v(c.value_pct)}`;
    case "max_weight_per_stock": return `Mã lớn nhất${c.ticker ? ` (${c.ticker})` : ""} ≤ ${fmt(c.limit_pct, 1)}% · thực tế ${v(c.value_pct)}`;
    case "min_cash_pct": return `Tiền mặt ≥ ${fmt(c.limit_pct, 1)}% · thực tế ${v(c.value_pct)}`;
    case "max_holdings": return `Tối đa ${c.limit} mã · thực tế ${c.value} mã`;
    case "exclusions": return `Không giữ mã/ngành bị loại${c.held?.length ? ` · vi phạm: ${c.held.join(", ")}` : ""}`;
    case "cash": return `Đủ tiền sau phí · tiền mặt còn ${vnd(c.value_vnd)} đ`;
    default: return c.rule;
  }
}
function usedRules(d) {
  const m = d.mandate, s = d.sources || {}, rows = [];
  const add = (f, label, val) => rows.push(`<tr><td>${label}</td><td>${val}</td><td><span class="src ${s[f] || "unset"}">${SRC_VI[s[f] || "unset"]}</span></td></tr>`);
  add("capital", "Số vốn", `${fmt(d.capital_vnd / 1e6, 0)} triệu đồng`);
  add("exclude_sectors", "Loại ngành", m.exclude_sectors.length ? m.exclude_sectors.map((x) => SECTOR_VI[x] || x).join(", ") : "—");
  add("exclude_tickers", "Loại mã", m.exclude_tickers.length ? m.exclude_tickers.join(", ") : "—");
  add("sector_caps", "Trần ngành", Object.keys(m.sector_caps).length ? Object.entries(m.sector_caps).map(([k, v]) => `${SECTOR_VI[k] || k} ≤ ${fmt(100 * v, 1)}%`).join(", ") : "—");
  add("max_weight_per_stock", "Mỗi mã tối đa", m.max_weight_per_stock != null ? fmt(100 * m.max_weight_per_stock, 1) + "%" : "—");
  add("max_holdings", "Tối đa số mã", m.max_holdings ?? "—");
  add("min_cash_pct", "Tiền mặt tối thiểu", m.min_cash_pct != null ? fmt(m.min_cash_pct, 1) + "%" : "—");
  return `<h4>Ràng buộc đã dùng cho lần chạy này</h4><table class="tbl small">${rows.join("")}</table>`;
}
async function showResult(d, st) {
  $("#out").classList.remove("hidden");
  $("#execLabel").innerHTML = execLabel(d.execution);
  const fe = d.feasibility || { blocking: [], notes: [] };
  if (d.status === "infeasible") {
    $("#resultBody").classList.add("hidden"); $("#insideRun").classList.add("hidden");
    $("#infeasible").innerHTML = `<div class="infeasible"><h4>Không có danh mục lô chẵn nào thỏa yêu cầu này</h4><ul>` +
      fe.blocking.map((r) => `<li><b>${r.message_vi}</b></li>`).join("") + `</ul>` +
      (fe.notes.length ? `<p class="muted">Ghi chú: ${fe.notes.map((r) => r.message_vi).join(" ")}</p>` : "") +
      `<p>Gợi ý: nới quy tắc bị nêu ở trên (ví dụ tăng “Mỗi mã tối đa”, bớt ngành bị loại, giảm tiền mặt giữ lại) hoặc tăng số vốn, rồi chạy lại. Không có lệnh nào được tạo.</p></div>` + usedRules(d);
    $("#out").scrollIntoView({ behavior: "smooth" });
    return;
  }
  $("#infeasible").innerHTML = ""; $("#resultBody").classList.remove("hidden"); $("#insideRun").classList.remove("hidden");
  const ag = d.portfolios.AGQO, rd = d.portfolios["nearest-lot rounding"];
  $("#resKpis").innerHTML = [[d.trades.length, "mã mua"], [vnd(d.fees_vnd) + " đ", "phí giao dịch ước tính"], [vnd(d.cash_after_vnd) + " đ", "tiền mặt còn lại sau phí"],
    [fmt(d.invested_pct_post_fee, 1) + "%", "tỷ lệ đầu tư trên NAV sau phí"], [fmt(ag.te_pct, 2) + "%", `sai số bám dự kiến (làm tròn: ${fmt(rd.te_pct, 2)}%)`]]
    .map(([v, l]) => `<div class="k"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  $("#trades").innerHTML = `<tr><th>Mã</th><th>Ngành</th><th>Số lô</th><th>Giá</th><th>Giá trị</th><th>Phí</th></tr>` +
    d.trades.map((t) => `<tr><td><b>${t.ticker}</b></td><td>${SECTOR_VI[t.sector] || t.sector}</td><td>${t.lots}</td><td>${vnd(t.price_vnd)}</td><td>${vnd(t.value_vnd)}</td><td>${vnd(t.fee_vnd)}</td></tr>`).join("") +
    `<tr><td colspan="5">Tổng phí</td><td>${vnd(d.fees_vnd)}</td></tr><tr><td colspan="5"><b>Tiền mặt còn lại</b></td><td><b>${vnd(d.cash_after_vnd)}</b></td></tr>` +
    `<tr><td colspan="5">NAV sau phí (cơ sở kiểm tra quy tắc)</td><td>${vnd(d.post_trade_nav_vnd)}</td></tr>`;
  $("#checks").innerHTML = d.checks.map((c) => `<li class="${c.ok ? "" : "bad"}">${checkLabel(c)}</li>`).join("") +
    `<li>${d.quantum.ran ? `Đã đối chiếu với tối ưu chính xác của toàn bộ 2<sup>${d.quantum.qubits}</sup> tổ hợp lô` : `Quyết định bằng tìm kiếm chính xác (${d.quantum.reason_vi || d.quantum.reason})`}</li>`;
  $("#notes").innerHTML = fe.notes.length ? `<div class="notes">${fe.notes.map((r) => `<p>ⓘ ${r.message_vi}</p>`).join("")}</div>` : "";
  const names = Object.keys(d.portfolios);
  chart("teBars").setOption({ ...BASE, grid: { left: 190, right: 60, top: 10, bottom: 20 }, tooltip: { ...BASE.tooltip },
    xAxis: { type: "value", name: "% / năm", ...AX }, yAxis: { type: "category", data: names.map((n) => PORT_VI[n]), inverse: true, ...AX, axisLabel: { color: C.text } },
    series: [{ type: "bar", data: names.map((n) => ({ value: d.portfolios[n].te_pct, itemStyle: { color: PORT_COLOR[n], borderRadius: [0, 6, 6, 0] } })), barWidth: 22,
      label: { show: true, position: "right", color: C.text, formatter: (p) => fmt(p.value, 2) + "%" } }] });
  const gain = rd.te_pct - ag.te_pct;
  $("#cmpCaption").innerHTML = `Hình. Sai số bám VN30 dự kiến (năm hoá) cho cùng tài khoản. So với làm tròn lô gần nhất, AGQO ${gain > 0.005 ? `giảm <b class="up">${fmt(gain, 2)} điểm %</b>` : gain < -0.005 ? `<b class="down">kém hơn ${fmt(-gain, 2)} điểm %</b>` : "<b>gần như bằng</b>"}` +
    `${d.portfolios["greedy lot filling"] ? `; thuật toán tham lam cổ điển đạt ${fmt(d.portfolios["greedy lot filling"].te_pct, 2)}%` : ""}. Đây là ước tính trước khi giao dịch, không phải kết quả tương lai.`;
  const ideal = d.portfolios["ideal (fractional shares)"].weights;
  const order = d.tickers.map((t, i) => i).sort((a, b) => ideal[b] - ideal[a]);
  chart("wChart").setOption({ ...BASE, grid: { left: 50, right: 20, top: 40, bottom: 60 }, legend: LEG, tooltip: { ...BASE.tooltip, trigger: "axis", valueFormatter: (v) => fmt(v, 1) + "%" },
    xAxis: { type: "category", data: order.map((i) => d.tickers[i]), ...AX, axisLabel: { color: C.muted, rotate: 60, fontSize: 11, fontFamily: "JetBrains Mono" } },
    yAxis: { type: "value", name: "% vốn", ...AX },
    series: names.map((n) => ({ name: PORT_VI[n], type: "bar", data: order.map((i) => +(100 * d.portfolios[n].weights[i]).toFixed(2)), itemStyle: { color: PORT_COLOR[n] }, barGap: "8%" })) });
  $("#usedRules").innerHTML = usedRules(d);
  $("#qasmBtn").style.display = d.qasm ? "" : "none"; $("#qasmBtn").href = `/api/qasm/${d.id}`;
  $("#explainBtn").style.display = d.evidence ? "" : "none";
  $("#explain").innerHTML = "";
  const panels = ["#p2", "#p3", "#p4", "#p5", "#p6"];
  if (d.quantum.ran) {
    $("#noQuantum").innerHTML = "";
    panels.forEach((p) => $(p).classList.remove("hidden"));
    renderMarket(d); renderHamiltonian(d); renderAI(d); renderCircuit(d); renderSampling(d);
  } else {
    panels.forEach((p) => $(p).classList.add("hidden"));
    $("#noQuantum").innerHTML = `Lần chạy này không dùng mạch lượng tử: ${d.quantum.reason_vi || d.quantum.reason}.`;
  }
  $("#insideRun").ontoggle = () => Object.values(charts).forEach((c) => c.resize());
  $("#out").scrollIntoView({ behavior: "smooth" });
}

/* ---------------- LLM explanation ---------------- */
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
  if (!LAST_RUN) return;
  const box = $("#explain");
  box.innerHTML = `<div class="explain"><span class="spinner"></span>Đang gửi bằng chứng do mã nguồn tạo cho Qwen3.8-27B…</div>`;
  try {
    const r = await api("/api/explain", { id: LAST_RUN.id });
    if (!r.job) { box.innerHTML = `<div class="explain">${r.note}. Bằng chứng LLM sẽ nhận:<pre class="code">${JSON.stringify(r.evidence, null, 1)}</pre></div>`; return; }
    const res = await pollJob(r.job, (s) => box.innerHTML = `<div class="explain"><span class="spinner"></span>Qwen3.8 đang viết giải thích (${s} giây${s > 20 ? "; GPU đang khởi động, lần đầu mất khoảng 6 phút" : ""})…</div>`);
    if (res.status !== "done" || !res.explanation) { box.innerHTML = `<div class="explain">Không nhận được giải thích (${res.error || "lỗi"}).</div>`; return; }
    const e = res.explanation, ck = res.check, bad = ck.unverified_numbers, attr = ck.attribution_issues || [];
    const badAttr = attr.map((i) => i.number.replace(/\./g, "").replace(",", "."));
    box.innerHTML = `<div class="explain"><p>${highlightNumbers(e.summary_vi, [...bad, ...badAttr])}</p>` +
      (e.trade_notes || []).map((t) => `<p>• <b>${t.ticker}</b> ${t.action} ${t.lots} lô: ${highlightNumbers(t.reason_vi, [...bad, ...badAttr])}</p>`).join("") +
      (e.risk_notes_vi || []).map((t) => `<p>⚠ ${highlightNumbers(t, [...bad, ...badAttr])}</p>`).join("") +
      `<p class="muted">Kiểm tra tự động: ${ck.ok ? `<b class="up">mọi con số khớp bằng chứng, đúng phương án, chỉ số và đơn vị</b>` :
        `<b class="down">${bad.length} số không có trong bằng chứng, ${ck.trade_mismatches.length} lệnh lệch, ${ck.context_issues.length} lỗi ngữ cảnh, ${attr.length} số gán sai phương án/đơn vị</b>`} · ${res.usage?.input_tokens || "?"} token vào, ${res.usage?.output_tokens || "?"} token ra · ${res.gpu || ""}</p></div>`;
  } catch (err) { box.innerHTML = `<div class="explain">Lỗi: ${err.message}</div>`; }
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
let SECTOR_OF = {};
(async function boot() {
  try {
    META = await api("/api/meta");
    SECTOR_OF = Object.fromEntries(META.stocks.map((s) => [s.ticker, s.sector]));
    $("#asof").textContent = `Dữ liệu đến ${META.date} · ${META.universe.length} mã VN30 · tính toán: ${META.compute === "modal" ? "Modal" : META.compute}`;
    const tape = META.stocks.map((s) => `<span><b>${s.ticker}</b>1 lô ${vnd(s.lot_vnd)} đ <span class="${s.lot_vnd > 2e6 ? "down" : "up"}">${fmt(100 * s.lot_vnd / 20e6)}% của 20tr</span></span>`).join("");
    $("#tape").innerHTML = tape + tape;
    const pick = ["Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này", "Ngân hàng tối đa 30%", "Tôi không thích rủi ro, hãy để 10% tiền mặt và mỗi cổ phiếu tối đa 8%",
      "Tôi muốn tập trung, chỉ 8 mã thôi", "Tôi muốn ít rủi ro hơn"];
    $("#examples").innerHTML = `<span class="muted" style="margin:0 6px 0 0">Ví dụ:</span>` + pick.map((e) => `<span class="chip">${e}</span>`).join("");
    document.querySelectorAll("#examples .chip").forEach((c) => c.onclick = () => { $("#instr").value = c.textContent; parseInstruction(); });
    if (!META.live_llm) { $("#liveLLM").checked = false; $("#liveLLM").disabled = true; }
    bindForm(); renderForm(); renderPresets();
    lotChart(20);
    $("#capSlider").oninput = (e) => { $("#capLabel").textContent = e.target.value; lotChart(+e.target.value); };
    $("#runBtn").onclick = runClicked; $("#parseBtn").onclick = parseInstruction; $("#explainBtn").onclick = explain;
    await story();
    // shareable link: /?preset=bank25_200&run=1   or   /?capital=20&q=Ngân hàng tối đa 30%&live=0
    const P = new URLSearchParams(location.search);
    if (P.get("live") === "0") $("#liveLLM").checked = false;
    if (P.get("preset")) await choosePreset(P.get("preset"));
    if (P.get("capital")) { FORM.capital = +P.get("capital"); SRC.capital = "user"; renderForm(); }
    if (P.get("q")) { $("#instr").value = P.get("q"); await parseInstruction(); }
    if (P.get("run") === "1" && !PENDING) { document.documentElement.style.scrollBehavior = "auto"; $("#try").scrollIntoView(); await runJob({ capital_million: FORM.capital, mandate: mandateOf(), sources: { ...SRC }, preset_id: PRESET, clarification_pending: false }); }
    document.body.dataset.done = "1";
  } catch (err) { toast("Không tải được dữ liệu: " + err.message, 8000); }
})();
