"use strict";

const WINDOW_COLORS = { "PaP": "var(--mo-orange)", "Post (1ª semana)": "var(--mo-black)" };
const KPI_SEG_COLORS = { resueltas: "var(--mo-orange)", pendientes: "var(--mo-orange-hover)" };
const KPI_TARGET_PCT = 75;

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// RAW_RELEASES viene definido en releases-data.js (cargado antes que este script).

function formatDate(fecha, month, year) {
  if (!fecha) return month + " " + year;
  return fecha.replace(/\.$/, "").replace("-", " ") + " " + year;
}

function buildReleases() {
  return RAW_RELEASES.map(([name, year, fecha, month, papEntrada, papResueltas, postEntrada, postResueltas], ri) => {
    const totalEntrada = papEntrada + postEntrada;
    const totalResueltas = papResueltas + postResueltas;
    const pctPaP = papEntrada ? Math.round(100 * papResueltas / papEntrada) : 0;
    const pctFirstWeek = postEntrada ? Math.round(100 * postResueltas / postEntrada) : 0;
    return {
      id: "rel-" + ri,
      name, year,
      date: formatDate(fecha, month, year),
      papEntrada, papResueltas, postEntrada, postResueltas,
      totalEntrada, totalResueltas,
      pctPaP, pctFirstWeek
    };
  });
}

const RELEASES = buildReleases();
const YEARS = [...new Set(RELEASES.map(r => r.year))].sort();
const CHART_COUNT_OPTIONS = [6, 12, 24, "Todas"];

const state = { selectedYear: "Todas", chartCount: 12 };

function computeViewModel() {
  const filtered = state.selectedYear === "Todas" ? RELEASES : RELEASES.filter(r => r.year === state.selectedYear);

  const yearChips = ["Todas", ...YEARS].map(y => ({ label: String(y), value: y, active: y === state.selectedYear }));
  const chartCountChips = CHART_COUNT_OPTIONS.map(c => ({ label: String(c), value: c, active: c === state.chartCount }));

  const chartReleases = state.chartCount === "Todas" ? filtered : filtered.slice(-state.chartCount);
  const maxCount = Math.max(1, ...chartReleases.map(r => r.totalEntrada));
  const niceMax = Math.max(5, Math.ceil(maxCount / 5) * 5);
  const n = chartReleases.length;
  const releaseBars = chartReleases.map(r => ({
    label: r.name,
    papEntrada: r.papEntrada,
    postEntrada: r.postEntrada,
    pctPaP: r.pctPaP,
    pctFirstWeek: r.pctFirstWeek,
    colStyle: "flex:1; height:100%; display:flex; align-items:flex-end; justify-content:center;",
    barStyle: "width:100%; max-width:44px; border-radius: 4px 4px 0 0; overflow:hidden; height:" + Math.round(100 * r.totalEntrada / niceMax) + "%; display:flex; flex-direction:column-reverse;",
    papSegStyle: "width:100%; background: " + WINDOW_COLORS["PaP"] + "; height:" + Math.round(100 * r.papEntrada / Math.max(1, r.totalEntrada)) + "%;",
    postSegStyle: "width:100%; background: " + WINDOW_COLORS["Post (1ª semana)"] + "; height:" + Math.round(100 * r.postEntrada / Math.max(1, r.totalEntrada)) + "%;"
  }));
  const ptX = (i) => ((i + 0.5) / n) * 100;
  const pointsPaP = chartReleases.map((r, i) => ptX(i) + "," + (100 - r.pctPaP)).join(" ");
  const pointsFirstWeek = chartReleases.map((r, i) => ptX(i) + "," + (100 - r.pctFirstWeek)).join(" ");
  const axisLeftTicks = [niceMax, Math.round(niceMax / 2), 0];
  const axisRightTicks = ["100%", "50%", "0%"];

  const kpiPap = buildKpiChartData(chartReleases, "papEntrada", "papResueltas", "pctPaP", WINDOW_COLORS["PaP"], "PaP");
  const kpiPost = buildKpiChartData(chartReleases, "postEntrada", "postResueltas", "pctFirstWeek", WINDOW_COLORS["Post (1ª semana)"], "1ª semana");

  return {
    periodLabel: (YEARS[0] + "–" + YEARS[YEARS.length - 1]) + " · " + RELEASES.length + " releases",
    yearChips, chartCountChips,
    releaseBars, pointsPaP, pointsFirstWeek, axisLeftTicks, axisRightTicks,
    kpiPap, kpiPost,
    releaseRows: filtered
  };
}

function buildKpiChartData(chartReleases, entradaField, resueltasField, pctField, lineColor, windowLabel) {
  const maxCount = Math.max(1, ...chartReleases.map(r => r[entradaField]));
  const niceMax = Math.max(5, Math.ceil(maxCount / 5) * 5);
  const n = chartReleases.length;
  const ptX = (i) => ((i + 0.5) / n) * 100;
  const bars = chartReleases.map((r) => {
    const total = r[entradaField];
    const resueltas = r[resueltasField];
    const pendientes = total - resueltas;
    return {
      label: r.name,
      resueltas, pendientes, pct: r[pctField], windowLabel, lineColor,
      colStyle: "flex:1; height:100%; display:flex; align-items:flex-end; justify-content:center;",
      barStyle: "width:100%; max-width:44px; border-radius: 4px 4px 0 0; overflow:hidden; height:" + Math.round(100 * total / niceMax) + "%; display:flex; flex-direction:column-reverse;",
      resueltasSegStyle: "width:100%; background: " + KPI_SEG_COLORS.resueltas + "; height:" + Math.round(100 * resueltas / Math.max(1, total)) + "%;",
      pendientesSegStyle: "width:100%; background: " + KPI_SEG_COLORS.pendientes + "; height:" + Math.round(100 * pendientes / Math.max(1, total)) + "%;"
    };
  });
  const points = chartReleases.map((r, i) => ptX(i) + "," + (100 - r[pctField])).join(" ");
  return {
    bars, points, lineColor, windowLabel,
    axisLeftTicks: [niceMax, Math.round(niceMax / 2), 0],
    axisRightTicks: ["100%", "50%", "0%"]
  };
}

function renderHeader(vm) {
  return `
    <div class="mo-topbar">
      <img src="../assets/masorange-logo-positive.svg" alt="MASORANGE">
      <div class="mo-topbar-sep"></div>
      <span class="mo-topbar-dept">Customer &amp; Service Operations</span>
      <nav class="mo-topbar-nav">
        <a href="../dashboard-portal.html">Portal</a>
        <a href="../massive-incidents-dashboard.html">Incidencias masivas</a>
        <a href="../postmortem-dashboard.html">Release</a>
        <a href="index.html" class="active">KPIs Release</a>
        <a href="/reportes-incidencias/index.html">Reportes de Incidencias</a>
        <a href="/problemas">Gestión de Problemas</a>
      </nav>
    </div>
    <div class="page-meta">
      <span class="page-meta-title">Dashboard de KPIs de Release</span>
      <span class="page-meta-period">Periodo: ${escapeHtml(vm.periodLabel)}</span>
    </div>`;
}

function renderYearFilter(vm) {
  const chips = vm.yearChips.map(chip =>
    `<button class="brand-chip${chip.active ? " active" : ""}" data-action="set-year" data-year="${escapeHtml(chip.label)}">${escapeHtml(chip.label)}</button>`
  ).join("");
  return `
    <div class="brand-filter">
      <span class="brand-filter-label">Año</span>
      ${chips}
    </div>`;
}

function renderChartCountFilter(vm) {
  const chips = vm.chartCountChips.map(chip =>
    `<button class="brand-chip${chip.active ? " active" : ""}" data-action="set-chart-count" data-count="${escapeHtml(chip.label)}">${escapeHtml(chip.label)}</button>`
  ).join("");
  return `
    <div class="brand-filter">
      <span class="brand-filter-label">Releases en gráficas</span>
      ${chips}
    </div>`;
}

function renderBarChart(vm) {
  const bars = vm.releaseBars.map(bar => {
    const tipLabel = bar.label + ": " + bar.papEntrada + " PaP (" + bar.pctPaP + "%) · " + bar.postEntrada + " Post (" + bar.pctFirstWeek + "%)";
    return `<div class="bar-col" tabindex="0" role="img" aria-label="${escapeHtml(tipLabel)}"
        data-label="${escapeHtml(bar.label)}" data-pap="${bar.papEntrada}" data-post="${bar.postEntrada}" data-pct-pap="${bar.pctPaP}" data-pct-post="${bar.pctFirstWeek}"
        style="${bar.colStyle}">
      <div style="${bar.barStyle}">
        <div class="bar-seg" style="${bar.papSegStyle}"></div>
        <div class="bar-seg" style="${bar.postSegStyle}"></div>
      </div>
    </div>`;
  }).join("");
  const labels = vm.releaseBars.map(bar =>
    `<div class="bar-label-col">
      <div class="bar-label-name">${escapeHtml(bar.label)}</div>
    </div>`
  ).join("");
  const leftTicks = vm.axisLeftTicks.map(t => `<div>${t}</div>`).join("");
  const rightTicks = vm.axisRightTicks.map(t => `<div>${t}</div>`).join("");

  return `
    <div class="card">
      <div class="chart-card-header">
        <div class="chart-title">Incidencias por release</div>
        <div class="chart-legend">
          <span><span class="legend-swatch" style="background: var(--mo-orange);"></span>PaP Entrada</span>
          <span><span class="legend-swatch" style="background: var(--mo-black);"></span>Post Entrada</span>
          <span><span class="legend-line" style="background: var(--accent);"></span>% PaP</span>
          <span><span class="legend-line" style="background: var(--mo-black);"></span>% 1ª semana</span>
        </div>
      </div>
      <div class="bar-chart">
        <div class="axis-left">${leftTicks}</div>
        <div class="bars-area">
          <div class="gridlines">
            <div class="gridline"></div>
            <div class="gridline"></div>
            <div class="gridline"></div>
          </div>
          <div class="bars">${bars}</div>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="bar-svg">
            <polyline points="${vm.pointsPaP}" fill="none" stroke="var(--mo-orange)" stroke-width="1.5" vector-effect="non-scaling-stroke" />
            <polyline points="${vm.pointsFirstWeek}" fill="none" stroke="var(--mo-black)" stroke-width="1.5" vector-effect="non-scaling-stroke" />
          </svg>
          <div class="chart-tooltip"></div>
        </div>
        <div class="axis-right">${rightTicks}</div>
      </div>
      <div class="bar-labels">
        ${labels}
        <div class="bar-labels-spacer"></div>
      </div>
    </div>`;
}

function renderKpiChart(chart, title) {
  const bars = chart.bars.map(bar => {
    const tipLabel = bar.label + ": " + bar.resueltas + " solucionadas, " + bar.pendientes + " pendientes (% " + bar.windowLabel + ": " + bar.pct + "%)";
    return `<div class="bar-col" tabindex="0" role="img" aria-label="${escapeHtml(tipLabel)}"
        data-label="${escapeHtml(bar.label)}" data-resueltas="${bar.resueltas}" data-pendientes="${bar.pendientes}" data-pct="${bar.pct}" data-pct-label="${escapeHtml(bar.windowLabel)}" data-line-color="${bar.lineColor}"
        style="${bar.colStyle}">
      <div style="${bar.barStyle}">
        <div class="bar-seg" style="${bar.resueltasSegStyle}"></div>
        <div class="bar-seg" style="${bar.pendientesSegStyle}"></div>
      </div>
    </div>`;
  }).join("");
  const labels = chart.bars.map(bar =>
    `<div class="bar-label-col">
      <div class="bar-label-name">${escapeHtml(bar.label)}</div>
    </div>`
  ).join("");
  const leftTicks = chart.axisLeftTicks.map(t => `<div>${t}</div>`).join("");
  const rightTicks = chart.axisRightTicks.map(t => `<div>${t}</div>`).join("");

  return `
    <div class="card">
      <div class="chart-card-header">
        <div class="chart-title">${escapeHtml(title)}</div>
        <div class="chart-legend">
          <span><span class="legend-swatch" style="background: ${KPI_SEG_COLORS.resueltas};"></span>Solucionadas</span>
          <span><span class="legend-swatch" style="background: ${KPI_SEG_COLORS.pendientes};"></span>Pendientes</span>
          <span><span class="legend-line" style="background: ${chart.lineColor};"></span>% ${escapeHtml(chart.windowLabel)}</span>
          <span><span class="legend-line legend-line-dashed"></span>Objetivo ${KPI_TARGET_PCT}%</span>
        </div>
      </div>
      <div class="bar-chart">
        <div class="axis-left">${leftTicks}</div>
        <div class="bars-area">
          <div class="gridlines">
            <div class="gridline"></div>
            <div class="gridline"></div>
            <div class="gridline"></div>
          </div>
          <div class="bars">${bars}</div>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="bar-svg">
            <line x1="0" y1="${100 - KPI_TARGET_PCT}" x2="100" y2="${100 - KPI_TARGET_PCT}" stroke="var(--success)" stroke-width="1.25" stroke-dasharray="4 3" vector-effect="non-scaling-stroke" />
            <polyline points="${chart.points}" fill="none" stroke="${chart.lineColor}" stroke-width="1.5" vector-effect="non-scaling-stroke" />
          </svg>
          <div class="chart-tooltip"></div>
        </div>
        <div class="axis-right">${rightTicks}</div>
      </div>
      <div class="bar-labels">
        ${labels}
        <div class="bar-labels-spacer"></div>
      </div>
    </div>`;
}

function kpiCellHtml(pct) {
  const met = pct >= KPI_TARGET_PCT;
  const cls = met ? "cell-kpi-met" : "cell-kpi-miss";
  const icon = met ? "✓" : "✕";
  return `<div class="${cls}"><span class="cell-kpi-icon">${icon}</span>${pct}%</div>`;
}

function renderTable(vm) {
  const rows = vm.releaseRows.map(r => `
    <div class="table-grid table-row">
      <div class="cell-name">${escapeHtml(r.name)}</div>
      <div class="cell-muted">${r.year}</div>
      <div class="cell-muted">${escapeHtml(r.date)}</div>
      <div class="cell-num">${r.totalEntrada}</div>
      <div class="cell-plain">${r.papEntrada}</div>
      <div class="cell-plain">${r.papResueltas}</div>
      ${kpiCellHtml(r.pctPaP)}
      <div class="cell-plain">${r.postEntrada}</div>
      <div class="cell-plain">${r.postResueltas}</div>
      ${kpiCellHtml(r.pctFirstWeek)}
    </div>`
  ).join("");

  return `
    <div class="table-card">
      <div class="table-header-bar">
        <div class="table-title">Releases</div>
        <div class="table-hint">${vm.releaseRows.length} releases en el periodo seleccionado</div>
      </div>
      <div class="table-scroll">
        <div class="table-grid table-head-row">
          <div>Release</div><div>Año</div><div>Fecha PaP</div><div>Incid.</div><div>Incid. PaP</div><div>Solución PaP</div><div>% PaP</div><div>Incid. 1ª sem.</div><div>Solución 1ª sem.</div><div>% 1ª sem.</div>
        </div>
        ${rows}
      </div>
    </div>`;
}

function render() {
  const vm = computeViewModel();
  const root = document.getElementById("root");
  root.innerHTML = `
    ${renderHeader(vm)}
    <div class="container">
      ${renderYearFilter(vm)}
      ${renderChartCountFilter(vm)}
      <div class="charts-row">
        ${renderBarChart(vm)}
      </div>
      <div class="kpi-charts-row">
        ${renderKpiChart(vm.kpiPap, "KPI % PaP")}
        ${renderKpiChart(vm.kpiPost, "KPI % 1ª semana")}
      </div>
      ${renderTable(vm)}
    </div>`;
}

function getTooltipFor(col) {
  const barsArea = col.closest(".bars-area");
  return barsArea ? barsArea.querySelector(".chart-tooltip") : null;
}

function buildBarTooltip(tooltip, col) {
  tooltip.textContent = "";
  const title = document.createElement("div");
  title.className = "chart-tooltip-title";
  title.textContent = col.dataset.label;
  tooltip.appendChild(title);

  const rows = col.dataset.pap !== undefined
    ? [
        { color: WINDOW_COLORS["PaP"], text: col.dataset.pap + " incid. PaP", sub: col.dataset.pctPap + "% resueltas" },
        { color: WINDOW_COLORS["Post (1ª semana)"], text: col.dataset.post + " incid. Post", sub: col.dataset.pctPost + "% resueltas" }
      ]
    : [
        { color: KPI_SEG_COLORS.resueltas, text: col.dataset.resueltas + " solucionadas" },
        { color: KPI_SEG_COLORS.pendientes, text: col.dataset.pendientes + " pendientes" },
        { color: col.dataset.lineColor, text: "% " + col.dataset.pctLabel + ": " + col.dataset.pct + "%" }
      ];

  rows.forEach(r => {
    const row = document.createElement("div");
    row.className = "chart-tooltip-row";
    const key = document.createElement("span");
    key.className = "chart-tooltip-key";
    key.style.background = r.color;
    const value = document.createElement("span");
    value.className = "chart-tooltip-value";
    value.textContent = r.text;
    row.append(key, value);
    if (r.sub) {
      const sub = document.createElement("span");
      sub.className = "chart-tooltip-sub";
      sub.textContent = " · " + r.sub;
      row.appendChild(sub);
    }
    tooltip.appendChild(row);
  });
}

function positionBarTooltip(tooltip, col) {
  if (!tooltip) return;
  const barsArea = col.closest(".bars-area");
  const bar = col.firstElementChild;
  if (!barsArea || !bar) return;
  const areaRect = barsArea.getBoundingClientRect();
  const colRect = col.getBoundingClientRect();
  const barRect = bar.getBoundingClientRect();
  tooltip.style.left = (colRect.left + colRect.width / 2 - areaRect.left) + "px";
  tooltip.style.top = Math.max(0, barRect.top - areaRect.top) + "px";
}

function showBarTooltip(col) {
  const tooltip = getTooltipFor(col);
  if (!tooltip) return;
  buildBarTooltip(tooltip, col);
  positionBarTooltip(tooltip, col);
  tooltip.classList.add("visible");
}

function hideBarTooltip(col) {
  const tooltip = getTooltipFor(col);
  if (tooltip) tooltip.classList.remove("visible");
}

const root = document.getElementById("root");

root.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  const action = el.dataset.action;
  if (action === "set-year") {
    state.selectedYear = el.dataset.year === "Todas" ? "Todas" : Number(el.dataset.year);
    render();
  } else if (action === "set-chart-count") {
    state.chartCount = el.dataset.count === "Todas" ? "Todas" : Number(el.dataset.count);
    render();
  }
});

root.addEventListener("pointerover", (e) => {
  const col = e.target.closest(".bar-col");
  if (col) showBarTooltip(col);
});

root.addEventListener("pointermove", (e) => {
  const col = e.target.closest(".bar-col");
  if (col) positionBarTooltip(getTooltipFor(col), col);
});

root.addEventListener("pointerout", (e) => {
  const col = e.target.closest(".bar-col");
  if (col && !col.contains(e.relatedTarget)) hideBarTooltip(col);
});

root.addEventListener("focusin", (e) => {
  const col = e.target.closest(".bar-col");
  if (col) showBarTooltip(col);
});

root.addEventListener("focusout", (e) => {
  const col = e.target.closest(".bar-col");
  if (col) hideBarTooltip(col);
});

render();
