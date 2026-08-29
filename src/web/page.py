"""Embedded token dashboard HTML."""

PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Swingbot tokens</title>
  <style>
    :root {
      --bg: #0b0d11;
      --panel: #12151c;
      --panel-2: #181c25;
      --line: #262c38;
      --text: #e7ecf5;
      --muted: #8b94a7;
      --gold: #e0b56a;
      --green: #5ee9a4;
      --red: #ff7a8a;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font: 14px/1.4 "Segoe UI", system-ui, sans-serif;
    }
    a { color: var(--gold); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .app {
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100%;
    }
    header {
      display: flex;
      align-items: center;
      gap: 24px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      flex-wrap: wrap;
    }
    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-left: auto;
    }
    .refresh {
      background: var(--panel-2);
      border: 1px solid var(--line);
      color: var(--text);
      border-radius: 6px;
      padding: 6px 12px;
      cursor: pointer;
      font: inherit;
    }
    .refresh:disabled { opacity: 0.5; cursor: default; }
    .fetch-status {
      color: var(--muted);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .fetch-status.err { color: var(--red); }
    .overlay {
      position: fixed;
      inset: 0;
      background: rgba(11, 13, 17, 0.78);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      z-index: 20;
      color: var(--muted);
    }
    .overlay[hidden] { display: none; }
    .spin {
      width: 28px;
      height: 28px;
      border: 2px solid var(--line);
      border-top-color: var(--gold);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .brand {
      font-size: 15px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--gold);
      font-weight: 700;
    }
    .stats { display: flex; gap: 18px; flex-wrap: wrap; }
    .stat { min-width: 72px; }
    .stat b { display: block; font-variant-numeric: tabular-nums; }
    .stat span { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
    .pos { color: var(--green); }
    .neg { color: var(--red); }
    main {
      display: grid;
      grid-template-columns: 400px 1fr;
      min-height: 0;
    }
    .list {
      border-right: 1px solid var(--line);
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 0;
      background: var(--panel);
    }
    .filters { padding: 12px; display: grid; gap: 12px; border-bottom: 1px solid var(--line); }
    input, select {
      width: 100%;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
    }
    .pills { display: flex; gap: 6px; }
    .pills button {
      flex: 1;
      background: var(--panel-2);
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 0;
      cursor: pointer;
      font: inherit;
    }
    .pills button.on { color: var(--text); border-color: var(--gold); }
    .tokens, .detail { overflow: auto; scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
    .tokens::-webkit-scrollbar, .detail::-webkit-scrollbar { width: 6px; }
    .tokens::-webkit-scrollbar-track, .detail::-webkit-scrollbar-track { background: transparent; }
    .tokens::-webkit-scrollbar-thumb, .detail::-webkit-scrollbar-thumb {
      background: var(--line);
      border-radius: 6px;
    }
    .tokens::-webkit-scrollbar-thumb:hover, .detail::-webkit-scrollbar-thumb:hover { background: var(--muted); }
    .row {
      display: grid;
      grid-template-columns: 10px 1fr auto;
      gap: 10px;
      padding: 10px 14px;
      border-bottom: 1px solid var(--line);
      cursor: pointer;
      align-items: center;
    }
    .row:hover, .row.active { background: var(--panel-2); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
    .dot.open { background: var(--green); }
    .dot.sold { background: var(--gold); }
    .sym { font-weight: 650; }
    .name { color: var(--muted); font-size: 12px; }
    .metrics { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; margin-top: 2px; }
    .row-pnl { font-variant-numeric: tabular-nums; font-size: 12px; text-align: right; }
    .row-hold { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; margin-top: 2px; text-align: right; }
    .detail { padding: 24px 28px 40px; }
    .empty { color: var(--muted); padding: 24px; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    .meta { color: var(--muted); margin-bottom: 18px; }
    .addr {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      font-family: ui-monospace, "Cascadia Mono", monospace;
      font-size: 12px;
      word-break: break-all;
    }
    .chip {
      background: var(--panel-2);
      border: 1px solid var(--line);
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      cursor: pointer;
      font: inherit;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin: 20px 0;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
    }
    .card span { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
    .card b { font-variant-numeric: tabular-nums; font-size: 18px; }
    h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin: 28px 0 10px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
    td { font-variant-numeric: tabular-nums; }
    .reason { color: var(--muted); font-size: 12px; }
    .tz { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; }
    .tz select { width: auto; padding: 6px 8px; }
    .chart-block { margin: 4px 0 8px; }
    .chart-wrap {
      position: relative;
      height: 420px;
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }
    #ohlcv { width: 100%; height: 100%; }
    .ohlc-hud {
      position: absolute;
      top: 8px;
      left: 10px;
      z-index: 4;
      font-variant-numeric: tabular-nums;
      font-size: 12px;
      color: var(--muted);
      pointer-events: none;
    }
    .ohlc-hud b { color: var(--text); font-weight: 600; }
    .ohlc-hud .up { color: var(--green); }
    .ohlc-hud .dn { color: var(--red); }
    .marker-tip {
      position: absolute;
      z-index: 6;
      transform: translate(-50%, 10px);
      background: var(--panel);
      border: 1px solid var(--line);
      color: var(--green);
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      pointer-events: none;
      white-space: nowrap;
    }
    .marker-tip.above { transform: translate(-50%, calc(-100% - 10px)); }
    .marker-tip.neg { color: var(--red); }
    .chart-reset {
      position: absolute;
      top: 8px;
      right: 10px;
      z-index: 4;
      background: var(--panel-2);
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 4px 8px;
      font: 11px inherit;
      cursor: pointer;
    }
    .chart-reset:hover { color: var(--text); }
    .added-line {
      position: absolute;
      top: 0;
      bottom: 26px;
      width: 0;
      border-left: 1px dashed var(--gold);
      z-index: 3;
      pointer-events: none;
    }
    .added-label {
      position: absolute;
      top: 8px;
      transform: translateX(6px);
      color: var(--gold);
      font-size: 10px;
      letter-spacing: 0.06em;
      white-space: nowrap;
    }
    .chart-msg {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--muted);
      z-index: 5;
      background: var(--bg);
    }
    .chart-msg[hidden] { display: none; }
    @media (max-width: 840px) {
      main { grid-template-columns: 1fr; grid-template-rows: 42vh 1fr; }
      .list { border-right: 0; border-bottom: 1px solid var(--line); }
      .chart-wrap { height: 360px; }
    }
  </style>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
  <div class="app">
    <header>
      <div class="brand">Swingbot</div>
      <div class="stats" id="stats"></div>
      <div class="header-right">
        <label class="tz">Timezone
          <select id="tzOffset"></select>
        </label>
        <span class="fetch-status" id="fetchStatus" hidden></span>
        <button class="refresh" id="refresh" type="button">Refresh</button>
      </div>
    </header>
    <main>
      <aside class="list">
        <div class="filters">
          <input id="q" placeholder="Search symbol, name, or address">
          <div class="pills">
            <button data-status="all" class="on">All</button>
            <button data-status="open">Open</button>
            <button data-status="sold">Sold</button>
          </div>
          <select id="sort">
            <option value="buy-desc">Latest buy</option>
            <option value="buy-asc">Earliest buy</option>
            <option value="symbol">Symbol</option>
            <option value="pnl-desc">PnL high → low</option>
            <option value="pnl-asc">PnL low → high</option>
            <option value="liq-desc">Liquidity high → low</option>
            <option value="liq-asc">Liquidity low → high</option>
            <option value="vol-desc">Volume high → low</option>
            <option value="vol-asc">Volume low → high</option>
            <option value="txn-desc">Txns high → low</option>
            <option value="txn-asc">Txns low → high</option>
            <option value="age-desc">Age high → low</option>
            <option value="age-asc">Age low → high</option>
            <option value="scan-desc">Scans high → low</option>
            <option value="scan-asc">Scans low → high</option>
          </select>
        </div>
        <div class="tokens" id="list"></div>
      </aside>
      <section class="detail" id="detail"><div class="empty">Select a token.</div></section>
    </main>
  </div>
  <div class="overlay" id="overlay">
    <div class="spin"></div>
    <div id="overlayText">Loading...</div>
  </div>
  <script>
    const DEX = "https://dexscreener.com/solana/";
    const GMGN = "https://gmgn.ai/sol/token/";
    const SOL = "https://solscan.io/token/";
    let tokens = [];
    let selected = new URLSearchParams(location.search).get("address");
    let statusFilter = "all";
    let loading = false;
    let candleTimer = null;
    let lastCandleDone = -1;
    let mintFetch = null;
    const CHART_UP = "#5ee9a4";
    const CHART_DOWN = "#ff7a8a";
    const CANDLE_UP_BODY = "#0c3d2e";
    const CANDLE_DOWN_BODY = "#4a1418";
    const CANDLE_UP_WICK = "#22c55e";
    const CANDLE_DOWN_WICK = "#ef4444";
    const CHART_VOL_UP = "rgba(94,233,164,0.4)";
    const CHART_VOL_DN = "rgba(255,122,138,0.4)";
    const CHART_GRID = "rgba(255,255,255,0.06)";
    const SUB = "₀₁₂₃₄₅₆₇₈₉";
    let offsetHours = Number(localStorage.getItem("chart_utc_offset") ?? "10");
    let chartAddress = null;
    let chart = emptySeries();
    let tvChart = null;
    let candleSeries = null;
    let volumeSeries = null;
    let resizeObs = null;

    const $ = (id) => document.getElementById(id);
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
    const cls = (n) => n == null ? "" : Number(n) >= 0 ? "pos" : "neg";
    const num = (n, d = 4) => n == null || n === "" ? "—" : Number(n).toLocaleString(undefined, {
      minimumFractionDigits: 0, maximumFractionDigits: d
    });
    const usdCompact = (n) => {
      if (n == null || n === "") return "—";
      const x = Number(n);
      if (Math.abs(x) >= 1e6) return "$" + (x / 1e6).toFixed(1) + "M";
      if (Math.abs(x) >= 1000) return "$" + (x / 1000).toFixed(1) + "k";
      return "$" + x.toFixed(0);
    };
    const usd = (n) => n == null || n === "" ? "—" : "$" + Number(n).toLocaleString(undefined, {
      maximumFractionDigits: Number(n) >= 1000 ? 0 : 2
    });
    const pnl = (n) => {
      if (n == null || n === "") return "—";
      const x = Number(n);
      return (x > 0 ? "+" : "") + x.toFixed(4);
    };
    const age = (n) => {
      if (n == null || n === "") return "—";
      const hours = Math.max(0, Math.round(Number(n) * 24));
      return Math.floor(hours / 24) + "d " + (hours % 24) + "h";
    };
    const tokenPrice = (n) => {
      if (n == null || n === "") return "—";
      const x = Number(n);
      if (!Number.isFinite(x)) return "—";
      if (x === 0) return "0";
      if (Math.abs(x) >= 1) return x.toFixed(4);
      return x.toPrecision(4);
    };
    const holdAge = (buyTime) => {
      if (!buyTime) return "—";
      const bought = Date.parse(String(buyTime).replace(" ", "T") + "+10:00");
      if (Number.isNaN(bought)) return "—";
      return age((Date.now() - bought) / 86400000);
    };

    function emptySeries() {
      return { t: [], o: [], h: [], l: [], c: [], v: [], fills: [], registered_at: null };
    }
    function offsetLabel(hours) {
      if (hours === 0) return "UTC";
      return "UTC" + (hours > 0 ? "+" : "") + hours;
    }
    function fillTzSelect() {
      const sel = $("tzOffset");
      if (!sel || sel.options.length) return;
      for (let h = -12; h <= 14; h++) {
        const opt = document.createElement("option");
        opt.value = String(h);
        opt.textContent = offsetLabel(h);
        if (h === offsetHours) opt.selected = true;
        sel.appendChild(opt);
      }
    }
    function formatGmgnPrice(n) {
      if (n == null || n === "" || !Number.isFinite(Number(n))) return "—";
      const x = Number(n);
      if (x === 0) return "0";
      const sign = x < 0 ? "-" : "";
      const a = Math.abs(x);
      if (a >= 1) return sign + a.toFixed(6).replace(/0+$/, "").replace(/\\.$/, "");
      const frac = a.toFixed(16).replace(/0+$/, "").slice(2);
      const zeros = frac.length - frac.replace(/^0+/, "").length;
      const digits = (frac.replace(/^0+/, "") || "0").slice(0, 4);
      if (zeros < 3) return sign + a.toFixed(zeros + 4).replace(/0+$/, "").replace(/\\.$/, "");
      const count = String(zeros).split("").map((d) => SUB[d]).join("");
      return sign + "0.0" + count + digits;
    }
    function shiftedTime(unix) { return unix + offsetHours * 3600; }
    function candleData() {
      return chart.t.map((t, i) => ({ time: shiftedTime(t), open: chart.o[i], high: chart.h[i], low: chart.l[i], close: chart.c[i] }));
    }
    function volumeData() {
      return chart.t.map((t, i) => ({
        time: shiftedTime(t),
        value: chart.v[i],
        color: chart.c[i] >= chart.o[i] ? CHART_VOL_UP : CHART_VOL_DN,
      }));
    }
    function nearestBarTime(unix) {
      if (!chart.t.length) return shiftedTime(unix);
      const target = shiftedTime(unix);
      let best = shiftedTime(chart.t[0]);
      let bestD = Infinity;
      for (const t of chart.t) {
        const s = shiftedTime(t);
        const d = Math.abs(s - target);
        if (d < bestD) { bestD = d; best = s; }
      }
      return best;
    }
    function tradeMarkers() {
      const byTime = {};
      (chart.fills || []).forEach((fill) => {
        if (!fill.block_time || fill.price == null) return;
        const buy = String(fill.action || "").toLowerCase() === "buy";
        const time = nearestBarTime(fill.block_time);
        if (buy) {
          if (byTime[time] && byTime[time]._buyPrice != null) return;
          byTime[time] = {
            time,
            position: "belowBar",
            color: CHART_UP,
            shape: "arrowUp",
            text: "BUY",
            id: "buy-" + time,
            _buyPrice: Number(fill.price),
          };
          return;
        }
        if (byTime[time] && byTime[time]._buyPrice != null) return;
        byTime[time] = {
          time,
          position: "aboveBar",
          color: CHART_DOWN,
          shape: "arrowDown",
          text: "SELL",
          id: "sell-" + time,
          _sellPrice: Number(fill.price),
          _pnl: sellFillPnl(fill),
        };
      });
      return Object.values(byTime).sort((a, b) => a.time - b.time);
    }
    function sellFillPnl(fill) {
      const token = tokens.find(t => t.address === selected);
      const sells = (token && token.sells) || [];
      if (sells.length && fill.block_time) {
        let best = null;
        let bestD = Infinity;
        for (const row of sells) {
          if (row.pnl == null || row.pnl === "" || !row.time) continue;
          const stamp = Date.parse(String(row.time).replace(" ", "T") + "+10:00") / 1000;
          if (!Number.isFinite(stamp)) continue;
          const delta = Math.abs(stamp - Number(fill.block_time));
          if (delta < bestD) { bestD = delta; best = Number(row.pnl); }
        }
        if (best != null && Number.isFinite(best) && bestD <= 3600) return best;
      }
      const buySol = (chart.fills || [])
        .filter(row => String(row.action || "").toLowerCase() === "buy")
        .reduce((sum, row) => sum + Math.abs(Number(row.sol_amount) || 0), 0);
      const sellSol = Math.abs(Number(fill.sol_amount) || 0);
      if (!buySol && !sellSol) return null;
      return sellSol - buySol;
    }
    function hideMarkerTip() {
      const tip = $("markerTip");
      if (tip) tip.hidden = true;
    }
    function showMarkerTip(param, markers) {
      const tip = $("markerTip");
      if (!tip || !tvChart || !candleSeries) return;
      const id = param && param.hoveredObjectId != null ? String(param.hoveredObjectId) : "";
      let marker = markers.find((row) => row.id && row.id === id && (row._buyPrice != null || row._sellPrice != null));
      if (!marker && param && param.time != null) {
        marker = markers.find((row) => row.time === param.time && (row._buyPrice != null || row._sellPrice != null));
      }
      if (!marker) {
        hideMarkerTip();
        return;
      }
      const x = tvChart.timeScale().timeToCoordinate(marker.time);
      if (x == null) { hideMarkerTip(); return; }
      const buy = marker._buyPrice != null;
      tip.hidden = false;
      tip.classList.toggle("above", !buy);
      tip.classList.toggle("neg", !buy && marker._pnl != null && Number(marker._pnl) < 0);
      if (buy) {
        tip.textContent = formatGmgnPrice(marker._buyPrice) + " SOL";
      } else {
        const pnlText = marker._pnl == null || marker._pnl === ""
          ? "—"
          : ((Number(marker._pnl) > 0 ? "+" : "") + Number(marker._pnl).toFixed(4));
        tip.textContent = formatGmgnPrice(marker._sellPrice) + " SOL  ·  " + pnlText + " SOL";
      }
      tip.style.left = Math.round(x) + "px";
      const y = param && param.point ? param.point.y : null;
      tip.style.top = Math.round(y != null ? y : 0) + "px";
    }
    function hudHtml(i) {
      if (i == null || i < 0 || !chart.t.length) return "";
      const o = chart.o[i], h = chart.h[i], l = chart.l[i], c = chart.c[i], v = chart.v[i];
      const tag = c >= o ? "up" : "dn";
      return `O <b class="${tag}">${formatGmgnPrice(o)}</b>
        H <b class="${tag}">${formatGmgnPrice(h)}</b>
        L <b class="${tag}">${formatGmgnPrice(l)}</b>
        C <b class="${tag}">${formatGmgnPrice(c)}</b>
        V <b>${Number(v).toFixed(2)}</b> SOL`;
    }
    function syncAddedLine() {
      const line = $("addedLine");
      if (!line || !tvChart) return;
      const t = chart.registered_at;
      if (t == null || !chart.t.length || t < chart.t[0] || t > chart.t[chart.t.length - 1]) {
        line.hidden = true;
        return;
      }
      const x = tvChart.timeScale().timeToCoordinate(shiftedTime(t));
      if (x == null) { line.hidden = true; return; }
      line.hidden = false;
      line.style.left = Math.round(x) + "px";
    }
    function destroyChart() {
      hideMarkerTip();
      if (resizeObs) { resizeObs.disconnect(); resizeObs = null; }
      if (tvChart) { tvChart.remove(); tvChart = null; }
      candleSeries = null;
      volumeSeries = null;
    }
    function setChartMsg(text) {
      const msg = $("chartMsg");
      if (!msg) return;
      if (!text) { msg.hidden = true; msg.textContent = ""; return; }
      msg.hidden = false;
      msg.textContent = text;
    }
    function drawChart() {
      const el = $("ohlcv");
      if (!el || typeof LightweightCharts === "undefined") return;
      destroyChart();
      setChartMsg("");
      tvChart = LightweightCharts.createChart(el, {
        layout: {
          background: { type: "solid", color: "#0b0d11" },
          textColor: "#8b94a7",
          fontSize: 11,
          fontFamily: "Segoe UI, system-ui, sans-serif",
        },
        grid: { vertLines: { color: CHART_GRID }, horzLines: { color: CHART_GRID } },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: { color: "rgba(255,255,255,0.18)", width: 1, style: 0, labelBackgroundColor: "#181c25" },
          horzLine: { color: "rgba(255,255,255,0.18)", width: 1, style: 0, labelBackgroundColor: "#181c25" },
        },
        rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.06, bottom: 0.22 } },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, rightOffset: 4 },
        handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
        localization: { priceFormatter: formatGmgnPrice },
      });
      candleSeries = tvChart.addCandlestickSeries({
        upColor: CANDLE_UP_BODY,
        downColor: CANDLE_DOWN_BODY,
        borderVisible: true,
        borderUpColor: CANDLE_UP_WICK,
        borderDownColor: CANDLE_DOWN_WICK,
        wickVisible: true,
        wickUpColor: CANDLE_UP_WICK,
        wickDownColor: CANDLE_DOWN_WICK,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineColor: "rgba(231,236,245,0.4)",
        priceLineWidth: 1,
        priceLineStyle: 2,
        priceFormat: { type: "custom", minMove: 1e-12, formatter: formatGmgnPrice },
      });
      volumeSeries = tvChart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "",
        lastValueVisible: false,
        priceLineVisible: false,
      });
      tvChart.priceScale("").applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
      candleSeries.setData(candleData());
      volumeSeries.setData(volumeData());
      const markers = tradeMarkers();
      if (markers.length) candleSeries.setMarkers(markers);
      tvChart.timeScale().fitContent();
      tvChart.subscribeCrosshairMove((param) => {
        const hud = $("ohlcHud");
        if (!hud) return;
        if (!param || !param.time || !chart.t.length) {
          hud.innerHTML = hudHtml(chart.t.length - 1);
          hideMarkerTip();
          return;
        }
        const unix = param.time - offsetHours * 3600;
        let i = chart.t.findIndex((t) => t === unix);
        if (i < 0) {
          i = chart.t.reduce((best, t, idx) => Math.abs(t - unix) < Math.abs(chart.t[best] - unix) ? idx : best, 0);
        }
        hud.innerHTML = hudHtml(i);
        showMarkerTip(param, markers);
      });
      tvChart.timeScale().subscribeVisibleLogicalRangeChange(syncAddedLine);
      const hud = $("ohlcHud");
      if (hud) hud.innerHTML = hudHtml(chart.t.length - 1);
      syncAddedLine();
      resizeObs = new ResizeObserver(() => {
        if (!tvChart || !el) return;
        tvChart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
        syncAddedLine();
      });
      resizeObs.observe(el);
    }
    function applyChartData(data) {
      chart = {
        t: data.t || [], o: data.o || [], h: data.h || [], l: data.l || [], c: data.c || [],
        v: data.v || [], fills: data.fills || [], registered_at: data.registered_at,
      };
      if (!chart.t.length) {
        destroyChart();
        chart = emptySeries();
        setChartMsg("No 5m candles for this mint.");
        return false;
      }
      drawChart();
      return true;
    }
    async function loadMintChart(address, update) {
      chartAddress = address;
      if (!tvChart) setChartMsg("Loading chart…");
      const cached = await fetch("/api/backtest/ohlcv?address=" + encodeURIComponent(address), { cache: "no-store" });
      if (chartAddress !== address) return;
      if (cached.ok) {
        const data = await cached.json();
        if (chartAddress !== address) return;
        applyChartData(data);
      } else {
        destroyChart();
        chart = emptySeries();
        setChartMsg(update ? "Fetching candles…" : "No 5m candles for this mint.");
      }
      if (!update || candleTimer) return;
      const token = tokens.find(t => t.address === address);
      const label = (token && token.symbol) || "token";
      mintFetch = address;
      setFetchStatus("Updating " + label + "…");
      try {
        const posted = await fetch("/api/backtest/ohlcv?address=" + encodeURIComponent(address), {
          method: "POST",
          cache: "no-store",
        });
        if (chartAddress !== address) return;
        if (posted.ok) {
          const data = await posted.json();
          if (chartAddress !== address) return;
          applyChartData(data);
        } else if (!tvChart) {
          setChartMsg("No 5m candles for this mint.");
        }
      } catch (_) {
        if (chartAddress === address && !tvChart) setChartMsg("No 5m candles for this mint.");
      } finally {
        if (mintFetch === address) mintFetch = null;
        if (!candleTimer) setFetchStatus("");
      }
    }
    function syncUrl() {
      if (!selected) return;
      const url = new URL(location.href);
      url.searchParams.set("address", selected);
      history.replaceState(null, "", url);
    }
    function showDetail(force) {
      const token = tokens.find(t => t.address === selected);
      if (!token) {
        destroyChart();
        chartAddress = null;
        $("detail").innerHTML = `<div class="empty">Select a token.</div>`;
        return;
      }
      if (!force && chartAddress === token.address && $("ohlcv")) return;
      destroyChart();
      $("detail").innerHTML = detail(token);
      loadMintChart(token.address, true);
    }

    function setOverlay(text) {
      $("overlay").hidden = false;
      const label = $("overlayText");
      if (label) label.textContent = text || "Loading...";
    }

    function setFetchStatus(text, error) {
      const el = $("fetchStatus");
      if (!el) return;
      if (!text) {
        el.hidden = true;
        el.textContent = "";
        el.classList.remove("err");
        return;
      }
      el.hidden = false;
      el.textContent = text;
      el.classList.toggle("err", !!error);
    }

    function candleStatusText(status) {
      const total = Number(status.total) || 0;
      const done = Number(status.done) || 0;
      if (total) {
        let text = "Candles " + done + "/" + total;
        if (status.symbol) text += " · " + status.symbol;
        return text;
      }
      return status.message || "Updating candles…";
    }

    function stopCandlePoll() {
      if (candleTimer) {
        clearInterval(candleTimer);
        candleTimer = null;
      }
    }

    async function pollCandles() {
      try {
        const status = await (await fetch("/api/backtest/refresh", { cache: "no-store" })).json();
        if (status.running) {
          setFetchStatus(candleStatusText(status));
          const done = Number(status.done) || 0;
          if (status.address && status.address === selected && done !== lastCandleDone) {
            lastCandleDone = done;
            loadMintChart(selected);
          }
          return;
        }
        stopCandlePoll();
        if (status.error) {
          setFetchStatus(status.error, true);
          return;
        }
        if ($("fetchStatus") && !$("fetchStatus").hidden) {
          setFetchStatus("Candles updated");
          if (selected) loadMintChart(selected);
          setTimeout(() => {
            const el = $("fetchStatus");
            if (el && el.textContent === "Candles updated") setFetchStatus("");
          }, 2500);
        }
      } catch (_) {}
    }

    function beginCandlePoll() {
      if (candleTimer) return;
      lastCandleDone = -1;
      pollCandles();
      candleTimer = setInterval(pollCandles, 1000);
    }

    async function startCandleRefreshBackground() {
      const res = await fetch("/api/backtest/refresh", { method: "POST", cache: "no-store" });
      if (!res.ok) throw new Error("failed to start candle update");
      setFetchStatus("Updating candles…");
      beginCandlePoll();
    }

    async function load(candles) {
      if (loading) return;
      loading = true;
      const first = !tokens.length;
      if (first) setOverlay("Loading...");
      $("refresh").disabled = true;
      try {
        if (candles) {
          try { await startCandleRefreshBackground(); }
          catch (err) { setFetchStatus((err && err.message) || "Candle update failed", true); }
        } else {
          try {
            const status = await (await fetch("/api/backtest/refresh", { cache: "no-store" })).json();
            if (status.running) {
              setFetchStatus(candleStatusText(status));
              beginCandlePoll();
            }
          } catch (_) {}
        }
        const res = await fetch("/api/tokens?live=1", { cache: "no-store" });
        const data = await res.json();
        tokens = data.tokens || [];
        renderStats(data.summary || {});
        if (selected && !tokens.some(t => t.address === selected)) selected = null;
        if (!selected && tokens.length) selected = tokens[0].address;
        syncUrl();
        renderList();
        showDetail(true);
      } finally {
        loading = false;
        $("overlay").hidden = true;
        $("refresh").disabled = false;
      }
    }

    function sumPnl(values) {
      let total = 0;
      let any = false;
      for (const value of values) {
        if (value == null || value === "") continue;
        total += Number(value);
        any = true;
      }
      return any ? total : null;
    }

    function renderStats(s) {
      const today = s.today || new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Vladivostok" });
      const daily = (s.daily_pnl || {})[today];
      const net = sumPnl(tokens.map(t => t.net_pnl));
      const realized = s.realized_pnl;
      const total = realized == null && net == null ? null : Number(realized || 0) + Number(net || 0);
      $("stats").innerHTML = [
        ["Tokens", s.token_count ?? 0],
        ["Open", s.open_count ?? 0],
        ["Sold", s.sold_count ?? 0],
        ["PnL", pnl(realized), cls(realized)],
        ["Net PnL", pnl(net), cls(net)],
        ["Total PnL", pnl(total), cls(total)],
        ["Today", pnl(daily), cls(daily)],
      ].map(([k, v, c]) => `<div class="stat"><b class="${c || ""}">${esc(v)}</b><span>${k}</span></div>`).join("");
    }

    function hasSold(t) {
      return t.status === "sold" || (t.sell_count || 0) > 0;
    }

    function rowPnl(t) {
      if (statusFilter === "sold" || t.status === "sold") return t.total_pnl;
      return t.net_pnl;
    }

    function rowAge(t) {
      return t.pair_age ?? t.last_pair_age;
    }

    function rowScanTotal(t) {
      if (t.scan_total != null && t.scan_total !== "") return Number(t.scan_total);
      const counts = t.scan_count || [];
      return counts.length ? counts.reduce((sum, n) => sum + (Number(n) || 0), 0) : null;
    }

    function cmpNum(a, b, desc) {
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return desc ? b - a : a - b;
    }

    function visible() {
      const q = $("q").value.trim().toLowerCase();
      const rows = tokens.filter(t => {
        if (statusFilter === "open" && t.status !== "open") return false;
        if (statusFilter === "sold" && !hasSold(t)) return false;
        if (!q) return true;
        return [t.symbol, t.name, t.address].some(v => String(v || "").toLowerCase().includes(q));
      });
      const sort = $("sort").value;
      rows.sort((a, b) => {
        if (sort === "symbol") return String(a.symbol || "").localeCompare(String(b.symbol || ""));
        if (sort === "buy-asc") return String(a.last_buy_time || "").localeCompare(String(b.last_buy_time || ""));
        if (sort === "pnl-desc") return cmpNum(rowPnl(a), rowPnl(b), true);
        if (sort === "pnl-asc") return cmpNum(rowPnl(a), rowPnl(b), false);
        if (sort === "liq-desc") return cmpNum(a.liquidity, b.liquidity, true);
        if (sort === "liq-asc") return cmpNum(a.liquidity, b.liquidity, false);
        if (sort === "vol-desc") return cmpNum(a.volume_24h, b.volume_24h, true);
        if (sort === "vol-asc") return cmpNum(a.volume_24h, b.volume_24h, false);
        if (sort === "txn-desc") return cmpNum(a.txns_24h, b.txns_24h, true);
        if (sort === "txn-asc") return cmpNum(a.txns_24h, b.txns_24h, false);
        if (sort === "age-desc") return cmpNum(rowAge(a), rowAge(b), true);
        if (sort === "age-asc") return cmpNum(rowAge(a), rowAge(b), false);
        if (sort === "scan-desc") return cmpNum(rowScanTotal(a), rowScanTotal(b), true);
        if (sort === "scan-asc") return cmpNum(rowScanTotal(a), rowScanTotal(b), false);
        return String(b.last_buy_time || "").localeCompare(String(a.last_buy_time || ""));
      });
      return rows;
    }

    function rowMeta(t) {
      if (statusFilter === "sold" || t.status === "sold") {
        return { text: pnl(t.total_pnl), cls: cls(t.total_pnl) };
      }
      return { text: pnl(t.net_pnl), cls: cls(t.net_pnl) };
    }

    function rowScans(t) {
      const counts = (t.scan_count || []).map(n => Number(n) || 0).filter(n => n > 0);
      if (counts.length > 1) return counts.join(" · ") + " scans";
      const n = counts.length ? counts[0] : t.scan_total;
      return (n == null ? 0 : n) + " scans";
    }

    function renderList() {
      const rows = visible();
      $("list").innerHTML = rows.length ? rows.map(t => {
        const meta = rowMeta(t);
        return `
        <div class="row ${t.address === selected ? "active" : ""}" data-addr="${esc(t.address)}">
          <div class="dot ${esc(t.status)}"></div>
          <div>
            <div class="sym">${esc(t.symbol)}</div>
            <div class="name">${esc(t.name)}</div>
            <div class="metrics">${usdCompact(t.liquidity_usd)} · ${usdCompact(t.volume_24h)} · ${t.txns_24h == null ? "—" : num(t.txns_24h, 0)} · ${age(t.pair_age)} · ${rowScans(t)}</div>
          </div>
          <div>
            <div class="row-pnl ${meta.cls}">${meta.text}</div>
            <div class="row-hold">${holdAge(t.last_buy_time)}</div>
          </div>
        </div>`;
      }).join("") : `<div class="empty">No tokens match.</div>`;
    }

    function detail(t) {
      const buys = (t.buys || []).map(b => `
        <tr>
          <td>${esc(b.time || "—")}</td>
          <td>${usd(b.liquidity)}</td>
          <td>${usd(b.volume_24h_usd)}</td>
          <td>${age(b.pair_age)}</td>
          <td class="reason">${esc(b.filter_reason || "—")}</td>
        </tr>`).join("") || `<tr><td colspan="5" class="reason">No buys yet.</td></tr>`;
      const sells = (t.sells || []).map(s => `
        <tr>
          <td>${esc(s.time || "—")}</td>
          <td class="${cls(s.pnl)}">${pnl(s.pnl)}</td>
          <td>${esc(s.reason || "—")}</td>
        </tr>`).join("") || `<tr><td colspan="3" class="reason">No sells yet.</td></tr>`;
      const scanGroups = t.scans || [];
      const scans = scanGroups.length ? scanGroups.map((group, gi) => {
        const rows = (group || []).map((s, si) => `
          <tr>
            <td>${esc(s.scan_time || "—")}${si === 0 ? ' <span class="reason">buy</span>' : ""}</td>
            <td>${usd(s.liquidity_usd)}</td>
            <td>${usd(s.volume_24h_usd)}</td>
            <td>${s.price == null || s.price === "" ? "—" : tokenPrice(s.price) + " SOL"}</td>
            <td class="reason">${esc(s.filter_reason || "—")}</td>
          </tr>`).join("") || `<tr><td colspan="5" class="reason">Empty group.</td></tr>`;
        return `
          <h2>Scans · buy ${gi + 1}</h2>
          <table>
            <thead><tr><th>Time</th><th>Liquidity</th><th>24h volume</th><th>Price</th><th>Filter</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>`;
      }).join("") : `<h2>Scans</h2><table><tbody><tr><td colspan="5" class="reason">No scans yet.</td></tr></tbody></table>`;
      return `
        <h1>${esc(t.symbol)}</h1>
        <div class="meta">${esc(t.name)} · ${esc(t.status)}</div>
        <div class="addr">
          <span>${esc(t.address)}</span>
          <button class="chip" data-copy="${esc(t.address)}">Copy</button>
          ${t.address ? `<a href="${DEX}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">Dexscreener</a>
          <a href="${GMGN}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">GMGN</a>
          <a href="${SOL}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">Solscan</a>` : ""}
        </div>
        <div class="cards">
          <div class="card"><span>Price</span><b>${t.price == null || t.price === "" ? "—" : tokenPrice(t.price) + " SOL"}</b></div>
          <div class="card"><span>Liquidity</span><b>${usd(t.liquidity_usd)}</b></div>
          <div class="card"><span>Pair age</span><b>${age(t.pair_age ?? t.last_pair_age)}</b></div>
          <div class="card"><span>24h volume</span><b>${usd(t.volume_24h)}</b></div>
          <div class="card"><span>24h txns</span><b>${t.txns_24h == null ? "—" : num(t.txns_24h, 0)}</b></div>
          <div class="card"><span>Scans</span><b>${t.scan_total == null ? "—" : num(t.scan_total, 0)}</b></div>
          <div class="card"><span>Net PnL</span><b class="${cls(t.net_pnl)}">${pnl(t.net_pnl)}</b></div>
        </div>
        <div class="chart-block">
          <div class="chart-wrap">
            <div class="chart-msg" id="chartMsg">Loading chart…</div>
            <div class="ohlc-hud" id="ohlcHud"></div>
            <div class="marker-tip" id="markerTip" hidden></div>
            <button class="chart-reset" id="chartReset" type="button">Reset</button>
            <div id="addedLine" class="added-line" hidden><span class="added-label">TOKEN ADDED</span></div>
            <div id="ohlcv"></div>
          </div>
        </div>
        <h2>Buys</h2>
        <table>
          <thead><tr><th>Time</th><th>Liquidity</th><th>24h volume</th><th>Age</th><th>Filter</th></tr></thead>
          <tbody>${buys}</tbody>
        </table>
        ${scans}
        <h2>Sells</h2>
        <table>
          <thead><tr><th>Time</th><th>PnL</th><th>Reason</th></tr></thead>
          <tbody>${sells}</tbody>
        </table>
      `;
    }

    $("q").addEventListener("input", renderList);
    $("sort").addEventListener("change", renderList);
    document.querySelectorAll(".pills button").forEach(btn => {
      btn.addEventListener("click", () => {
        statusFilter = btn.dataset.status;
        document.querySelectorAll(".pills button").forEach(b => b.classList.toggle("on", b === btn));
        renderList();
      });
    });
    $("list").addEventListener("click", (e) => {
      const row = e.target.closest(".row");
      if (!row) return;
      selected = row.dataset.addr;
      syncUrl();
      renderList();
      showDetail(false);
    });
    $("detail").addEventListener("click", async (e) => {
      if (e.target.id === "chartReset" && tvChart) {
        tvChart.timeScale().fitContent();
        return;
      }
      const btn = e.target.closest("[data-copy]");
      if (!btn) return;
      try { await navigator.clipboard.writeText(btn.dataset.copy); btn.textContent = "Copied"; }
      catch { btn.textContent = "Copy failed"; }
      setTimeout(() => { btn.textContent = "Copy"; }, 1200);
    });
    $("tzOffset").addEventListener("change", () => {
      offsetHours = Number($("tzOffset").value);
      localStorage.setItem("chart_utc_offset", String(offsetHours));
      if (chart.t.length && $("ohlcv")) drawChart();
    });
    $("refresh").addEventListener("click", () => load(true));
    fillTzSelect();
    load();
  </script>
</body>
</html>
"""
