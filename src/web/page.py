"""Embedded OHLC curve dashboard HTML."""

import json

from src.config.structure import as_dict as structure_params
from src.config.telegram import LOCAL_TIMEZONE

_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Swingbot curves</title>
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
      gap: 20px;
      margin-left: auto;
    }
    .header-right .stats { justify-content: flex-end; }
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
    .stats { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }
    .stat { min-width: 64px; }
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
      grid-template-columns: 10px 1fr;
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
    .sym {
      font-weight: 650;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .metrics { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; margin-top: 2px; }
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
    .chip.on { border-color: var(--gold); color: var(--gold); }
    .chart-bias { color: var(--muted); font-size: 12px; }
    .chart-bias b { font-weight: 650; text-transform: capitalize; }
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
    .chart-panel { margin: 8px 0 24px; }
    .chart-toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
    .chart-toolbar select { width: auto; min-width: 92px; }
    .chart-params { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 8px; }
    .chart-param {
      display: flex;
      align-items: center;
      gap: 5px;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .chart-param input {
      width: 64px;
      height: 32px;
      min-width: 0;
      padding: 6px 8px;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
    }
    .chart-param-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 10px;
      align-items: center;
      padding: 8px 12px;
      min-height: 48px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
    }
    .chart-ohlc {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      color: var(--muted);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      min-height: 18px;
      margin-top: 8px;
    }
    .chart-ohlc b { color: var(--text); font-weight: 600; }
    .chart-ohlc .up b { color: var(--green); }
    .chart-ohlc .down b { color: var(--red); }
    .chart-stage {
      position: relative;
      height: min(62vh, 640px);
      min-height: 420px;
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }
    .chart-empty {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--muted);
      z-index: 6;
    }
    .chart-empty[hidden] { display: none !important; }
    .mint { font-family: ui-monospace, "Cascadia Mono", monospace; font-size: 13px; }
    @media (max-width: 840px) {
      main { grid-template-columns: 1fr; grid-template-rows: 42vh 1fr; }
      .list { border-right: 0; border-bottom: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="brand">Swingbot</div>
      <div class="stats" id="counts"></div>
      <div class="header-right">
        <div class="stats" id="stats"></div>
        <button class="refresh" id="refresh" type="button">Refresh</button>
      </div>
    </header>
    <main>
      <aside class="list">
        <div class="filters">
          <input id="q" placeholder="Search name, mint or wallet">
          <select id="wallet"></select>
          <select id="sort">
            <option value="latest">Latest candle</option>
            <option value="change-desc">Change high → low</option>
            <option value="change-asc">Change low → high</option>
            <option value="age-desc">Age high → low</option>
            <option value="age-asc">Age low → high</option>
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
  <script src="/static/lightweight-charts.js"></script>
  <script>
    const DEX = "https://dexscreener.com/solana/";
    const GMGN = "https://gmgn.ai/sol/token/";
    const SOL = "https://solscan.io/token/";
    const params = new URLSearchParams(location.search);
    let tokens = [];
    let selected = params.get("address");
    let chartInterval = ["15s","30s","1m","5m","15m"].includes(params.get("interval")) ? params.get("interval") : "1m";
    let chartWallet = params.has("wallet") ? (params.get("wallet") || "") : null;
    let chartData = null;
    let overviewData = null;
    let chartAbort = null;
    let detailAbort = null;
    let tvChart = null;
    let candleSeries = null;
    let lineSeries = null;
    let swingSeries = null;
    let volumeSeries = null;
    let showPivots = true;
    let showAcceptedOpposites = true;
    let showSwingLine = true;
    let showKama = false;
    let showKamaPivots = false;
    let showKamaAcceptedOpposites = false;
    let showTrades = true;
    let ignoreRange = false;
    let rangeTimer = null;
    let loading = false;
    let meTrades = [];
    const INTERVALS = ["15s", "30s", "1m", "5m", "15m"];
    const STRUCTURE_DEFAULTS = __STRUCTURE_CONFIG__;
    const LOCAL_TZ = __LOCAL_TIMEZONE__;
    const PIVOT_LEFT = STRUCTURE_DEFAULTS.PIVOT_LEFT;
    const PIVOT_RIGHT = STRUCTURE_DEFAULTS.PIVOT_RIGHT;
    let ATR_PERIOD = STRUCTURE_DEFAULTS.ATR_PERIOD;
    let PIVOT_ATR_MULT = STRUCTURE_DEFAULTS.PIVOT_ATR_MULT;
    let KAMA_PIVOT_ATR_MULT = STRUCTURE_DEFAULTS.KAMA_PIVOT_ATR_MULT;
    let MIN_PRICE_DISTANCE = STRUCTURE_DEFAULTS.MIN_PRICE_DISTANCE;
    let MIN_BAR_DISTANCE = STRUCTURE_DEFAULTS.MIN_BAR_DISTANCE;
    let KAMA_PERIOD = STRUCTURE_DEFAULTS.KAMA_PERIOD;
    let KAMA_FAST = STRUCTURE_DEFAULTS.KAMA_FAST;
    let KAMA_SLOW = STRUCTURE_DEFAULTS.KAMA_SLOW;
    let KAMA_SLOPE = STRUCTURE_DEFAULTS.KAMA_SLOPE;
    let KAMA_FLAT_ATR = STRUCTURE_DEFAULTS.KAMA_FLAT_ATR;

    const $ = (id) => document.getElementById(id);
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
    const num = (n, d = 4) => n == null || n === "" ? "—" : Number(n).toLocaleString(undefined, {
      minimumFractionDigits: 0, maximumFractionDigits: d
    });
    const usd = (n) => n == null || n === "" ? "—" : "$" + Number(n).toLocaleString(undefined, {
      maximumFractionDigits: Number(n) >= 1000 ? 0 : 2
    });
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
    const shortMint = (a) => !a ? "—" : a.slice(0, 4) + "…" + a.slice(-4);
    const tokenLabel = (t) => (t && (t.name || t.symbol)) || shortMint(t && t.address);
    const ageSec = (s) => (s == null || s === "") ? "—" : age(Number(s) / 86400);
    const when = (unix) => {
      if (unix == null || unix === "") return "—";
      const parts = new Intl.DateTimeFormat("en-GB", {
        timeZone: LOCAL_TZ,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
        hourCycle: "h23",
      }).formatToParts(new Date(Number(unix) * 1000));
      const get = (type) => (parts.find(p => p.type === type) || {}).value || "";
      return get("year") + "-" + get("month") + "-" + get("day")
        + " " + get("hour") + ":" + get("minute") + ":" + get("second");
    };

    function chartTime(unix) {
      const t = typeof unix === "object" && unix != null ? (unix.timestamp ?? unix) : unix;
      return new Date(Number(t) * 1000);
    }

    function chartTick(time, tickMarkType) {
      const d = chartTime(time);
      const opts = { timeZone: LOCAL_TZ };
      if (tickMarkType === 0) return d.toLocaleString("en-US", { ...opts, year: "numeric" });
      if (tickMarkType === 1) return d.toLocaleString("en-US", { ...opts, month: "short", year: "numeric" });
      if (tickMarkType === 2) return d.toLocaleString("en-US", { ...opts, month: "short", day: "numeric" });
      if (tickMarkType === 4) {
        return d.toLocaleString("en-US", {
          ...opts, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
        });
      }
      return d.toLocaleString("en-US", { ...opts, hour: "2-digit", minute: "2-digit", hour12: false });
    }

    function syncUrl() {
      const url = new URL(location.href);
      url.searchParams.delete("view");
      if (selected) url.searchParams.set("address", selected);
      else url.searchParams.delete("address");
      url.searchParams.delete("range");
      url.searchParams.delete("mode");
      url.searchParams.set("interval", chartInterval);
      if (chartWallet) url.searchParams.set("wallet", chartWallet);
      else url.searchParams.delete("wallet");
      history.replaceState(null, "", url);
    }

    function showDetail() {
      const token = tokens.find(t => t.address === selected);
      destroyChart();
      if (!token) {
        $("detail").innerHTML = `<div class="empty">Select a token.</div>`;
        return;
      }
      $("detail").innerHTML = detail(token);
      bindChartControls();
      loadCurve(token);
    }

    function setOverlay(text) {
      $("overlay").hidden = false;
      const label = $("overlayText");
      if (label) label.textContent = text || "Loading...";
    }

    async function refreshSelected() {
      if (loading) return;
      const token = tokens.find(t => t.address === selected);
      if (!token) return load();
      loading = true;
      $("refresh").disabled = true;
      setOverlay("Fetching OHLC...");
      try {
        const res = await fetch("/api/ohlc/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
          body: JSON.stringify({
            address: token.address,
            wallet: chartWallet || token.wallet,
            interval: token.interval,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || "refresh failed");
      } catch (err) {
        setOverlay(err && err.message ? err.message : "Refresh failed");
        await new Promise(r => setTimeout(r, 900));
      } finally {
        loading = false;
      }
      await load();
    }

    async function load() {
      if (loading) return;
      loading = true;
      const first = !tokens.length;
      if (first || !$("overlay").hidden) setOverlay($("overlayText").textContent || "Loading curves...");
      $("refresh").disabled = true;
      try {
        const qs = chartWallet == null ? "" : ("?wallet=" + encodeURIComponent(chartWallet || "all"));
        const res = await fetch("/api/ohlc/tokens" + qs, { cache: "no-store" });
        const data = await res.json();
        tokens = data.tokens || [];
        fillWallets(data.wallets || [], data.wallet);
        renderStats(data.summary || {});
        if (selected && !tokens.some(t => t.address === selected)) selected = null;
        if (!selected && tokens.length) selected = tokens[0].address;
        syncUrl();
        renderList();
        showDetail();
      } finally {
        loading = false;
        $("overlay").hidden = true;
        $("refresh").disabled = false;
      }
    }

    function fillWallets(wallets, fallback) {
      if (chartWallet == null) chartWallet = fallback || "";
      const opts = [`<option value="">All wallets</option>`]
        .concat(wallets.map(w => `<option value="${esc(w)}">${esc(shortMint(w))}</option>`));
      $("wallet").innerHTML = opts.join("");
      $("wallet").value = wallets.includes(chartWallet) ? chartWallet : "";
      if (!wallets.includes(chartWallet)) chartWallet = "";
    }

    function pnlClass(n) {
      const x = Number(n);
      if (!Number.isFinite(x) || x === 0) return "";
      return x > 0 ? "pos" : "neg";
    }
    function sol(n, signed = true) {
      if (n == null || n === "") return "—";
      const x = Number(n);
      if (!Number.isFinite(x)) return "—";
      const sign = signed && x > 0 ? "+" : "";
      return sign + x.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
    }
    function renderStats(s) {
      const bt = s.backtest || {};
      const counts = [
        ["Wallets", s.wallet_count ?? 0, ""],
        ["Tokens", s.token_count ?? 0, ""],
      ];
      const items = [
        ["Realized", sol(bt.realized_pnl), pnlClass(bt.realized_pnl)],
        ["Unrealized", sol(bt.unrealized_pnl), pnlClass(bt.unrealized_pnl)],
        ["Total PnL", sol(bt.total_pnl), pnlClass(bt.total_pnl)],
        ["W / L / Trades", `${bt.wins ?? 0} / ${bt.losses ?? 0} / ${bt.trades ?? 0}`, ""],
        ["Fees", sol(bt.fees_total, false), ""],
      ];
      const html = (rows) => rows.map(([k, v, cls]) =>
        `<div class="stat"><b class="${cls}">${esc(v)}</b><span>${k}</span></div>`
      ).join("");
      const countsEl = $("counts");
      if (countsEl) countsEl.innerHTML = html(counts);
      $("stats").innerHTML = html(items);
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
        if (!q) return true;
        return [t.name, t.symbol, t.address, t.wallet, ...(t.wallets || [])].some(v => String(v || "").toLowerCase().includes(q));
      });
      const sort = $("sort").value;
      rows.sort((a, b) => {
        if (sort === "change-desc") return cmpNum(a.change_pct, b.change_pct, true);
        if (sort === "change-asc") return cmpNum(a.change_pct, b.change_pct, false);
        if (sort === "age-desc") return cmpNum(a.age_seconds, b.age_seconds, true);
        if (sort === "age-asc") return cmpNum(a.age_seconds, b.age_seconds, false);
        return cmpNum(a.time_to, b.time_to, true);
      });
      return rows;
    }

    function renderList() {
      const rows = visible();
      $("list").innerHTML = rows.length ? rows.map(t => `
        <div class="row ${t.address === selected ? "active" : ""}" data-addr="${esc(t.address)}">
          <div class="dot ${Number(t.change_pct) >= 0 ? "open" : "sold"}"></div>
          <div>
            <div class="sym">${esc(tokenLabel(t))}</div>
            <div class="metrics">${esc(t.interval || "1m")} · ${ageSec(t.age_seconds)}</div>
          </div>
        </div>`).join("") : `<div class="empty">No OHLC files match.</div>`;
    }

    function detail(t) {
      const intervals = INTERVALS.map(r =>
        `<option value="${r}" ${r === chartInterval ? "selected" : ""}>${r}</option>`
      ).join("");
      const bt = t.backtest || {};
      return `
        <h1>${esc(tokenLabel(t))}</h1>
        <div class="meta">${esc([t.symbol, t.interval || "1m"].filter(Boolean).join(" · "))}</div>
        <div class="addr">
          <span>${esc(t.address)}</span>
          <button class="chip" data-copy="${esc(t.address)}">Copy</button>
          <a href="${DEX}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">Dexscreener</a>
          <a href="${GMGN}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">GMGN</a>
          <a href="${SOL}${encodeURIComponent(t.address)}" target="_blank" rel="noreferrer">Solscan</a>
        </div>
        <div class="cards">
          <div class="card"><span>Last</span><b>${tokenPrice(t.last)}</b></div>
          <div class="card"><span>Age</span><b>${ageSec(t.age_seconds)}</b></div>
          <div class="card"><span>Realized</span><b class="${pnlClass(bt.realized_pnl)}">${esc(sol(bt.realized_pnl))}</b></div>
          <div class="card"><span>Unrealized</span><b class="${pnlClass(bt.unrealized_pnl)}">${esc(sol(bt.unrealized_pnl))}</b></div>
          <div class="card"><span>Total PnL</span><b class="${pnlClass(bt.total_pnl)}">${esc(sol(bt.total_pnl))}</b></div>
          <div class="card"><span>W / L / Trades</span><b>${esc(`${bt.wins ?? 0} / ${bt.losses ?? 0} / ${bt.trades ?? 0}`)}</b></div>
          <div class="card"><span>Fees</span><b>${esc(sol(bt.fees_total, false))}</b></div>
        </div>
        <div class="chart-panel">
          <div class="chart-toolbar">
            <select id="interval">${intervals}</select>
            <button class="chip ${showPivots ? "on" : ""}" id="pivotToggle" type="button">Pivot</button>
            <button class="chip ${showAcceptedOpposites ? "on" : ""}" id="acceptedOppositeToggle" type="button" title="First opposite pivot that passes all filters and locks the preceding pivot">Accepted opposite</button>
            <button class="chip ${showSwingLine ? "on" : ""}" id="swingLineToggle" type="button">Line</button>
            <button class="chip ${showKama ? "on" : ""}" id="kamaToggle" type="button">KAMA</button>
            <button class="chip ${showKamaPivots ? "on" : ""}" id="kamaPivotToggle" type="button">KAMA Pivot</button>
            <button class="chip ${showKamaAcceptedOpposites ? "on" : ""}" id="kamaAcceptedOppositeToggle" type="button" title="First opposite KAMA pivot that passes all filters and locks the preceding KAMA pivot">KAMA Accepted opposite</button>
            <button class="chip ${showTrades ? "on" : ""}" id="tradeToggle" type="button">Buy/Sell</button>
            <span class="chart-bias" id="chartBias"></span>
          </div>
          <div class="chart-params" id="structureParams">
            <div class="chart-param-group">
              <label class="chart-param">ATR <input id="pAtrPeriod" type="number" min="1" step="1"></label>
              <label class="chart-param" title="Reversal from pivot high/low to confirming close, in ATR units; 0 disables">pivot × <input id="pPivotAtrMult" type="number" min="0" step="0.1"></label>
            </div>
            <div class="chart-param-group">
              <label class="chart-param">min price <input id="pMinPriceDist" type="number" min="0" step="0.001"></label>
              <label class="chart-param">bars <input id="pMinBars" type="number" min="0" step="1"></label>
            </div>
            <div class="chart-param-group">
              <label class="chart-param">KAMA <input id="pKamaPeriod" type="number" min="1" step="1"></label>
              <label class="chart-param">fast <input id="pKamaFast" type="number" min="1" step="1"></label>
              <label class="chart-param">slow <input id="pKamaSlow" type="number" min="1" step="1"></label>
              <label class="chart-param" title="KAMA pivot reversal to confirming candle close, in ATR units; 0 disables">pivot × <input id="pKamaPivotAtrMult" type="number" min="0" step="0.1"></label>
              <label class="chart-param">slope <input id="pKamaSlope" type="number" min="1" step="1"></label>
              <label class="chart-param">flat <input id="pKamaFlat" type="number" min="0" step="0.01"></label>
            </div>
          </div>
          <div class="chart-stage" id="chartStage">
            <div class="chart-empty" id="chartEmpty">Loading chart...</div>
          </div>
          <div class="chart-ohlc" id="chartOhlc"></div>
        </div>
      `;
    }

    function bindChartControls() {
      if (!$("chartStage")) return;
      $("interval").addEventListener("change", () => {
        chartInterval = $("interval").value;
        syncUrl();
        const token = tokens.find(t => t.address === selected);
        if (token) loadCurve(token);
      });
      bindOverlayToggle("pivotToggle", () => { showPivots = !showPivots; });
      bindOverlayToggle("acceptedOppositeToggle", () => { showAcceptedOpposites = !showAcceptedOpposites; });
      bindOverlayToggle("swingLineToggle", () => { showSwingLine = !showSwingLine; });
      bindOverlayToggle("kamaToggle", () => { showKama = !showKama; });
      bindOverlayToggle("kamaPivotToggle", () => { showKamaPivots = !showKamaPivots; });
      bindOverlayToggle("kamaAcceptedOppositeToggle", () => { showKamaAcceptedOpposites = !showKamaAcceptedOpposites; });
      bindOverlayToggle("tradeToggle", () => { showTrades = !showTrades; });
      fillStructureInputs();
      let paramTimer = null;
      document.querySelectorAll("#structureParams input").forEach(input => {
        input.addEventListener("input", () => {
          clearTimeout(paramTimer);
          paramTimer = setTimeout(() => onStructureParamChange(false), 80);
        });
        input.addEventListener("change", () => onStructureParamChange(true));
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { e.preventDefault(); onStructureParamChange(true); }
        });
      });
    }

    function bindOverlayToggle(id, flip) {
      const btn = $(id);
      if (!btn) return;
      btn.addEventListener("click", () => {
        flip();
        btn.classList.toggle("on");
        if (tvChart) applyStructure((chartData && chartData.points) || []);
      });
    }

    function fillStructureInputs() {
      const set = (id, value) => { const el = $(id); if (el) el.value = value; };
      set("pAtrPeriod", ATR_PERIOD);
      set("pPivotAtrMult", PIVOT_ATR_MULT);
      set("pKamaPivotAtrMult", KAMA_PIVOT_ATR_MULT);
      set("pMinPriceDist", MIN_PRICE_DISTANCE);
      set("pMinBars", MIN_BAR_DISTANCE);
      set("pKamaPeriod", KAMA_PERIOD);
      set("pKamaFast", KAMA_FAST);
      set("pKamaSlow", KAMA_SLOW);
      set("pKamaSlope", KAMA_SLOPE);
      set("pKamaFlat", KAMA_FLAT_ATR);
    }

    function readNum(id, fallback, min) {
      const n = Number($(id) && $(id).value);
      if (!Number.isFinite(n)) return fallback;
      return min == null ? n : Math.max(min, n);
    }

    function onStructureParamChange(normalize) {
      ATR_PERIOD = Math.max(1, Math.round(readNum("pAtrPeriod", ATR_PERIOD, 1)));
      PIVOT_ATR_MULT = readNum("pPivotAtrMult", PIVOT_ATR_MULT, 0);
      KAMA_PIVOT_ATR_MULT = readNum("pKamaPivotAtrMult", KAMA_PIVOT_ATR_MULT, 0);
      MIN_PRICE_DISTANCE = Math.max(0, readNum("pMinPriceDist", MIN_PRICE_DISTANCE, 0));
      MIN_BAR_DISTANCE = Math.max(0, Math.round(readNum("pMinBars", MIN_BAR_DISTANCE, 0)));
      KAMA_PERIOD = Math.max(1, Math.round(readNum("pKamaPeriod", KAMA_PERIOD, 1)));
      KAMA_FAST = Math.max(1, Math.round(readNum("pKamaFast", KAMA_FAST, 1)));
      KAMA_SLOW = Math.max(1, Math.round(readNum("pKamaSlow", KAMA_SLOW, 1)));
      KAMA_SLOPE = Math.max(1, Math.round(readNum("pKamaSlope", KAMA_SLOPE, 1)));
      KAMA_FLAT_ATR = Math.max(0, readNum("pKamaFlat", KAMA_FLAT_ATR, 0));
      if (normalize) fillStructureInputs();
      if (tvChart) applyStructure((chartData && chartData.points) || []);
    }

    function setChartEmpty(text) {
      const empty = $("chartEmpty");
      if (!empty) return;
      if (!text) {
        empty.hidden = true;
        return;
      }
      empty.hidden = false;
      empty.textContent = text;
    }

    async function loadCurve(token) {
      if (chartAbort) chartAbort.abort();
      chartAbort = new AbortController();
      if (detailAbort) detailAbort.abort();
      clearTimeout(rangeTimer);
      const request = chartAbort;
      if (!tvChart) setChartEmpty("Loading chart...");
      const qs = new URLSearchParams({ address: token.address, interval: chartInterval });
      if (chartWallet) qs.set("wallet", chartWallet);
      else if (token.wallet) qs.set("wallet", token.wallet);
      try {
        const res = await fetch("/api/ohlc/curve?" + qs.toString(), {
          cache: "no-store",
          signal: chartAbort.signal,
        });
        if (!res.ok) throw new Error("missing");
        const loaded = await res.json();
        if (request !== chartAbort || request.signal.aborted) return;
        overviewData = loaded;
        chartData = overviewData;
        meTrades = overviewData.me || [];
        const points = chartData.points || [];
        if (!points.length) {
          destroyChart();
          setChartEmpty("No candles in this range.");
          return;
        }
        setChartEmpty(null);
        drawChart(true);
      } catch (err) {
        if (err.name === "AbortError") return;
        chartData = null;
        overviewData = null;
        meTrades = [];
        destroyChart();
        setChartEmpty("Could not load OHLCV.");
      }
    }

    function destroyChart() {
      const firstBuyLine = $("walletFirstBuyLine");
      if (firstBuyLine) firstBuyLine.remove();
      if (tvChart) {
        tvChart.remove();
        tvChart = null;
      }
      candleSeries = null;
      lineSeries = null;
      swingSeries = null;
      volumeSeries = null;
    }

    function mergePoints(base, extra) {
      if (!extra.length) return base;
      const from = extra[0].t, to = extra[extra.length - 1].t;
      return base.filter(p => p.t < from || p.t > to).concat(extra).sort((a, b) => a.t - b.t);
    }

    function seriesData(points) {
      const candles = [];
      const line = [];
      const volume = [];
      const seen = new Set();
      for (const p of points) {
        const time = Number(p.t);
        if (!Number.isFinite(time) || seen.has(time)) continue;
        seen.add(time);
        const bull = Number(p.c) >= Number(p.o);
        candles.push({ time, open: p.o, high: p.h, low: p.l, close: p.c });
        line.push({ time, value: p.c });
        volume.push({
          time,
          value: p.v_usd || p.v || 0,
          color: bull ? "rgba(38,166,154,0.45)" : "rgba(239,83,80,0.45)",
        });
      }
      return { candles, line, volume };
    }

    function structureRows(points) {
      const rows = [];
      const seen = new Set();
      for (const p of points) {
        const t = Number(p.t ?? p.time);
        const h = Number(p.h ?? p.high);
        const l = Number(p.l ?? p.low);
        const c = Number(p.c ?? p.close);
        const o = Number(p.o ?? p.open);
        if (!Number.isFinite(t) || !Number.isFinite(h) || !Number.isFinite(l) || !Number.isFinite(c) || seen.has(t)) continue;
        seen.add(t);
        rows.push({ t, o: Number.isFinite(o) ? o : c, h, l, c });
      }
      return rows;
    }

    function lastAtr(atr, i) {
      for (let j = i; j >= 0; j--) if (atr[j] != null) return atr[j];
      return 0;
    }

    function wilderAtr(rows, period) {
      const atr = new Array(rows.length).fill(null);
      if (!rows.length) return atr;
      const trs = rows.map((row, i) => {
        if (i === 0) return row.h - row.l;
        const prev = rows[i - 1].c;
        return Math.max(row.h - row.l, Math.abs(row.h - prev), Math.abs(row.l - prev));
      });
      if (trs.length < period) return atr;
      let value = 0;
      for (let i = 0; i < period; i++) value += trs[i];
      value /= period;
      atr[period - 1] = value;
      for (let i = period; i < trs.length; i++) {
        value = (value * (period - 1) + trs[i]) / period;
        atr[i] = value;
      }
      return atr;
    }

    function kamaValues(rows, period, fast, slow) {
      const out = new Array(rows.length).fill(null);
      if (rows.length <= period) return out;
      const fastSc = 2 / (fast + 1);
      const slowSc = 2 / (slow + 1);
      let value = rows[period].c;
      out[period] = value;
      for (let i = period + 1; i < rows.length; i++) {
        const change = Math.abs(rows[i].c - rows[i - period].c);
        let volatility = 0;
        for (let j = i - period + 1; j <= i; j++) volatility += Math.abs(rows[j].c - rows[j - 1].c);
        const er = volatility === 0 ? 0 : change / volatility;
        const sc = (er * (fastSc - slowSc) + slowSc) ** 2;
        value = value + sc * (rows[i].c - value);
        out[i] = value;
      }
      return out;
    }

    function kamaFilter(price, kama, atr, i) {
      const current = kama[i];
      const previous = i >= KAMA_SLOPE ? kama[i - KAMA_SLOPE] : null;
      if (current == null || previous == null) return "neutral";
      const noise = lastAtr(atr, i) * KAMA_FLAT_ATR;
      const delta = current - previous;
      if (Math.abs(delta) <= noise) return "neutral";
      if (price > current && delta > 0) return "bullish";
      if (price < current && delta < 0) return "bearish";
      return "neutral";
    }

    function detectKamaPivots(rows, kama, left, right, atr) {
      const pivots = [];
      const size = Math.min(rows.length, kama.length);
      for (let i = left + right; i < size; i++) {
        const mid = i - right;
        const value = kama[mid];
        if (value == null) continue;
        let isHigh = true, isLow = true;
        for (let j = mid - left; j <= mid + right; j++) {
          if (j === mid) continue;
          const other = kama[j];
          if (other == null) { isHigh = false; isLow = false; break; }
          if (other > value || (j > mid && other === value)) isHigh = false;
          if (other < value || (j > mid && other === value)) isLow = false;
          if (!isHigh && !isLow) break;
        }
        if (!isHigh && !isLow) continue;
        if (KAMA_PIVOT_ATR_MULT > 0) {
          if (atr[i] == null) continue;
          const threshold = atr[i] * KAMA_PIVOT_ATR_MULT;
          isHigh = isHigh && value - rows[i].c >= threshold;
          isLow = isLow && rows[i].c - value >= threshold;
        }
        if (!isHigh && !isLow) continue;
        pivots.push({
          i,
          t: rows[mid].t,
          value,
          price: value,
          kind: isHigh && isLow ? "both" : (isHigh ? "high" : "low"),
        });
      }
      return pivots;
    }


    function detectPivots(rows, left, right, atr = wilderAtr(rows, ATR_PERIOD)) {
      const pivots = [];
      for (let i = left + right; i < rows.length; i++) {
        const mid = i - right;
        const high = rows[mid].h, low = rows[mid].l;
        let isHigh = true, isLow = true;
        for (let j = mid - left; j <= mid + right; j++) {
          if (j === mid) continue;
          if (rows[j].h > high || (j > mid && rows[j].h === high)) isHigh = false;
          if (rows[j].l < low || (j > mid && rows[j].l === low)) isLow = false;
          if (!isHigh && !isLow) break;
        }
        if (PIVOT_ATR_MULT > 0) {
          if (atr[i] == null) continue;
          const threshold = atr[i] * PIVOT_ATR_MULT;
          isHigh = isHigh && high - rows[i].c >= threshold;
          isLow = isLow && rows[i].c - low >= threshold;
        }
        if (!isHigh && !isLow) continue;
        pivots.push({ i, t: rows[mid].t, price: rows[mid].c, kind: isHigh && isLow ? "both" : (isHigh ? "high" : "low") });
      }
      return pivots;
    }

    function filterPivots(raw, acceptedOpposites = []) {
      const out = [];
      for (const candidate of raw) {
        const previous = out[out.length - 1];
        const pivot = candidate.kind === "both"
          ? { ...candidate, kind: previous && previous.kind === "high" ? "low" : "high" }
          : candidate;
        const price = Math.abs(pivot.price) || 0;
        if (!out.length) { out.push(pivot); continue; }
        const last = out[out.length - 1];
        if (pivot.kind === last.kind) {
          const replaces = pivot.kind === "high" ? pivot.price >= last.price : pivot.price <= last.price;
          if (replaces) {
            out[out.length - 1] = pivot;
          }
          continue;
        }
        const move = pivot.kind === "low" ? last.price - pivot.price : pivot.price - last.price;
        if (move <= 0) continue;
        const base = Math.abs(last.price) || price;
        if (MIN_PRICE_DISTANCE > 0 && base && (move / base) <= MIN_PRICE_DISTANCE) continue;
        if (pivot.kind === "low" && MIN_BAR_DISTANCE > 0 && (pivot.i - last.i) < MIN_BAR_DISTANCE) continue;
        out.push(pivot);
        // Preserve the original accepted opposite even if this swing is replaced.
        acceptedOpposites.push({ ...pivot });
      }
      return out;
    }

    function classifyPivots(pivots) {
      let lastHigh = null, lastLow = null;
      for (const pivot of pivots) {
        if (pivot.kind === "high") {
          pivot.label = lastHigh == null ? "H" : (pivot.price > lastHigh.price ? "HH" : "LH");
          lastHigh = pivot;
        } else {
          pivot.label = lastLow == null ? "L" : (pivot.price > lastLow.price ? "HL" : "LL");
          lastLow = pivot;
        }
      }
    }

    function trendAfter(trend, lastHigh, lastLow) {
      const highLabel = lastHigh && lastHigh.label;
      const lowLabel = lastLow && lastLow.label;
      if (highLabel === "HH" && lowLabel === "HL") return "bullish";
      if (highLabel === "LH" && lowLabel === "LL") return "bearish";
      return trend;
    }

    function analyzeStructure(points) {
      const rows = structureRows(points);
      const empty = { pivots: [], accepted_opposites: [], kama: [], kama_pivots: [], kama_accepted_opposites: [], trend: "neutral", kama_filter: "neutral", last_high: null, last_low: null };
      if (rows.length < PIVOT_LEFT + PIVOT_RIGHT + 1) return empty;
      const atr = wilderAtr(rows, ATR_PERIOD);
      const kama = kamaValues(rows, KAMA_PERIOD, KAMA_FAST, KAMA_SLOW);
      const kamaAcceptedOpposites = [];
      const kamaPivots = filterPivots(
        detectKamaPivots(rows, kama, PIVOT_LEFT, PIVOT_RIGHT, atr),
        kamaAcceptedOpposites
      );
      const acceptedOpposites = [];
      const swings = filterPivots(detectPivots(rows, PIVOT_LEFT, PIVOT_RIGHT, atr), acceptedOpposites);
      classifyPivots(swings);
      const confirmAt = new Map();
      for (const pivot of swings) {
        const key = pivot.i;
        if (!confirmAt.has(key)) confirmAt.set(key, []);
        confirmAt.get(key).push(pivot);
      }
      let trend = "neutral";
      let lastHigh = null, lastLow = null;
      const pub = (p) => p && ({ t: p.t, price: p.price, kind: p.kind, label: p.label });
      for (let i = 0; i < rows.length; i++) {
        for (const pivot of (confirmAt.get(i) || [])) {
          if (pivot.kind === "high") { lastHigh = pivot; }
          else { lastLow = pivot; }
          trend = trendAfter(trend, lastHigh, lastLow);
        }
      }
      const last = rows.length - 1;
      return {
        pivots: swings.map(pub),
        accepted_opposites: acceptedOpposites.map(pub),
        kama: kama.map((value, i) => value == null ? null : ({ t: rows[i].t, value })).filter(Boolean),
        kama_pivots: kamaPivots.map(p => ({ t: p.t, value: p.value, kind: p.kind })),
        kama_accepted_opposites: kamaAcceptedOpposites.map(p => ({ t: p.t, value: p.value, kind: p.kind })),
        trend,
        kama_filter: kamaFilter(rows[last].c, kama, atr, last),
        last_high: pub(lastHigh),
        last_low: pub(lastLow),
      };
    }

    function chartTradeMarks(points) {
      // Never let trades outside candle data snap onto an edge candle.
      const times = new Set(points.map(p => p.t));
      const step = { "15s": 15, "1m": 60, "5m": 300, "15m": 900 }[chartInterval] || 60;
      const marks = [];
      for (const mark of meTrades) {
        if (!mark || !Number.isFinite(mark.t)) continue;
        if (mark.side !== "buy" && mark.side !== "sell") continue;
        const time = times.has(mark.t) ? mark.t : Math.floor(mark.t / step) * step;
        if (!times.has(time)) continue;
        marks.push({ ...mark, t: time });
      }
      return marks;
    }

    function structureMarkers(s, trades) {
      const markers = [];
      const seen = new Set();
      const add = (item) => {
        if (!item || seen.has(item.time)) return;
        seen.add(item.time);
        markers.push(item);
      };
      const seenTrades = new Set();
      for (const p of showTrades ? trades : []) {
        if (!p) continue;
        const buy = p.side === "buy";
        const position = buy ? "belowBar" : "aboveBar";
        const color = buy ? "#22c55e" : "#ef4444";
        const key = `${p.t}:${p.side}`;
        if (seenTrades.has(key)) continue;
        seenTrades.add(key);
        markers.push({
          time: p.t,
          position,
          color,
          shape: "circle",
          text: buy ? "BUY" : "SELL",
          size: 2,
        });
      }
      if (showPivots) {
        for (const p of s.pivots || []) {
          const high = p.kind === "high";
          add({
            time: p.t,
            position: high ? "aboveBar" : "belowBar",
            color: high ? "#ff7a8a" : "#5ee9a4",
            shape: high ? "arrowDown" : "arrowUp",
            text: p.label || "",
            size: 2,
          });
        }
      }
      if (showAcceptedOpposites) {
        for (const p of s.accepted_opposites || []) {
          markers.push({
            time: p.t,
            position: p.kind === "high" ? "aboveBar" : "belowBar",
            color: p.kind === "high" ? "#fb923c" : "#fbbf24",
            shape: "square",
            text: p.kind === "high" ? "Accepted H" : "Accepted L",
            size: 1,
          });
        }
      }
      markers.sort((a, b) => a.time - b.time);
      return markers;
    }

    function setBiasLegend(s) {
      const el = $("chartBias");
      if (!el) return;
      if (!s) { el.innerHTML = ""; return; }
      const trendCls = s.trend === "bullish" ? "pos" : s.trend === "bearish" ? "neg" : "";
      const kamaCls = s.kama_filter === "bullish" ? "pos" : s.kama_filter === "bearish" ? "neg" : "";
      el.innerHTML = `Trend <b class="${trendCls}">${esc(s.trend)}</b>`
        + (showKama ? ` · KAMA <b class="${kamaCls}">${esc(s.kama_filter)}</b>` : "");
    }

    function kamaPivotMarkers(s) {
      if (!showKama) return [];
      const markers = (showKamaPivots ? s.kama_pivots || [] : []).map(p => {
        const high = p.kind === "high";
        return {
          time: p.t,
          position: high ? "aboveBar" : "belowBar",
          color: high ? "#f472b6" : "#a78bfa",
          shape: high ? "arrowDown" : "arrowUp",
          text: high ? "KAMA H" : "KAMA L",
          size: 1,
        };
      });
      if (showKamaAcceptedOpposites) {
        for (const p of s.kama_accepted_opposites || []) {
          markers.push({
            time: p.t,
            position: p.kind === "high" ? "aboveBar" : "belowBar",
            color: p.kind === "high" ? "#22d3ee" : "#60a5fa",
            shape: "square",
            text: p.kind === "high" ? "KAMA Accepted H" : "KAMA Accepted L",
            size: 1,
          });
        }
      }
      markers.sort((a, b) => a.time - b.time);
      return markers;
    }

    function applyStructure(points) {
      try {
        if (!candleSeries) return;
        const trades = chartTradeMarks(points);
        if (!showPivots && !showAcceptedOpposites && !showSwingLine && !showKama && !(showTrades && trades.length)) {
          if (candleSeries.setMarkers) candleSeries.setMarkers([]);
          if (lineSeries) lineSeries.applyOptions({ visible: false });
          if (swingSeries) swingSeries.applyOptions({ visible: false });
          setBiasLegend(null);
          return;
        }
        const s = analyzeStructure(points);
        if (candleSeries.setMarkers) candleSeries.setMarkers(structureMarkers(s, trades));
        if (lineSeries) {
          lineSeries.setData(s.kama.map(p => ({ time: p.t, value: p.value })));
          if (lineSeries.setMarkers) lineSeries.setMarkers(kamaPivotMarkers(s));
          lineSeries.applyOptions({
            visible: showKama,
            color: "#38bdf8",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
        }
        if (swingSeries) {
          swingSeries.setData(s.pivots.map(p => ({ time: p.t, value: p.price })));
          swingSeries.applyOptions({ visible: showSwingLine });
        }
        setBiasLegend((showPivots || showSwingLine || showKama) ? s : null);
      } catch (err) {
        setBiasLegend(null);
      }
    }

    function setOhlcLegend(p) {
      const el = $("chartOhlc");
      if (!el) return;
      if (!p) { el.innerHTML = ""; return; }
      const bull = Number(p.close ?? p.c) >= Number(p.open ?? p.o);
      el.className = "chart-ohlc " + (bull ? "up" : "down");
      const o = p.open ?? p.o, h = p.high ?? p.h, l = p.low ?? p.l, c = p.close ?? p.c;
      const vol = p.v_usd != null ? p.v_usd : p.value;
      el.innerHTML = `
        <span>O <b>${esc(tokenPrice(o))}</b></span>
        <span>H <b>${esc(tokenPrice(h))}</b></span>
        <span>L <b>${esc(tokenPrice(l))}</b></span>
        <span>C <b>${esc(tokenPrice(c))}</b></span>
        <span>Vol <b>${esc(usd(vol))}</b></span>
        <span>${esc(when(p.time || p.t))}</span>`;
    }

    function updateWalletFirstBuyLine() {
      const host = $("chartStage");
      if (!host || !tvChart) return;
      let line = $("walletFirstBuyLine");
      if (!line) {
        line = document.createElement("div");
        line.id = "walletFirstBuyLine";
        line.style.cssText = "position:absolute;top:0;border-left:2px dashed #f8fafc;pointer-events:none;z-index:3;display:none";
        const label = document.createElement("span");
        label.textContent = "Target wallet first buy";
        label.style.cssText = "position:absolute;top:8px;left:5px;white-space:nowrap;color:#f8fafc;background:#181c25;padding:3px 5px;font-size:11px";
        line.appendChild(label);
        host.appendChild(line);
      }
      line.style.display = "none";
      const entry = chartData && chartData.target_wallet_first_entry;
      const t = entry && entry.t;
      if (entry) line.firstChild.textContent = `Target wallet first ${entry.side === "sell" ? "sell" : "buy"} · ${when(t)} (${LOCAL_TZ})`;
      const points = (chartData && chartData.points) || [];
      if (t == null || !points.length) return;
      const step = { "15s": 15, "30s": 30, "1m": 60, "5m": 300, "15m": 900 }[chartInterval];
      if (t < points[0].t || t >= points[points.length - 1].t + step) return;
      const scale = tvChart.timeScale();
      const index = points.findIndex(p => p.t > t);
      const left = index < 0 ? points.length - 1 : index - 1;
      if (left < 0) return;
      const nextTime = index < 0 ? points[left].t + step : points[index].t;
      const leftX = scale.timeToCoordinate(points[left].t);
      if (leftX == null) return;
      let rightX;
      if (index >= 0) {
        rightX = scale.timeToCoordinate(points[index].t);
      } else {
        const logical = scale.coordinateToLogical(leftX);
        rightX = logical == null ? null : scale.logicalToCoordinate(logical + 1);
      }
      if (rightX == null) return;
      const x = leftX + (rightX - leftX) * (t - points[left].t) / (nextTime - points[left].t);
      if (!Number.isFinite(x) || x < 0 || x > scale.width()) return;
      line.style.left = `${x}px`;
      line.style.bottom = `${scale.height()}px`;
      line.firstChild.style.transform = x > scale.width() - 160 ? "translateX(calc(-100% - 10px))" : "";
      line.style.display = "block";
    }

    function applyVisibleRange() {
      if (!tvChart) return;
      ignoreRange = true;
      tvChart.timeScale().fitContent();
      requestAnimationFrame(() => { ignoreRange = false; });
    }

    function onVisibleRange(range) {
      if (ignoreRange || !range || !selected) return;
      clearTimeout(rangeTimer);
      rangeTimer = setTimeout(() => loadVisibleDetail(range), 180);
    }

    async function loadVisibleDetail(range) {
      const token = tokens.find(t => t.address === selected);
      if (!token || !overviewData) return;
      const span = Number(range.to) - Number(range.from);
      if (!Number.isFinite(span) || span <= 0) return;
      if (detailAbort) detailAbort.abort();
      detailAbort = new AbortController();
      const request = detailAbort;
      const overview = overviewData;
      const qs = new URLSearchParams({
        address: token.address,
        interval: chartInterval,
        from: String(Math.floor(range.from)),
        to: String(Math.ceil(range.to)),
      });
      if (chartWallet) qs.set("wallet", chartWallet);
      else if (token.wallet) qs.set("wallet", token.wallet);
      try {
        const res = await fetch("/api/ohlc/curve?" + qs.toString(), {
          cache: "no-store",
          signal: detailAbort.signal,
        });
        if (!res.ok) return;
        const data = await res.json();
        if (request !== detailAbort || request.signal.aborted || overview !== overviewData || token.address !== selected) return;
        const extra = data.points || [];
        if (!extra.length) return;
        chartData = {
          ...overviewData,
          resolution: "detail",
          points: mergePoints(overviewData.points || [], extra),
        };
        drawChart(false);
      } catch (err) {
        if (err.name !== "AbortError") return;
      }
    }

    function drawChart(resetView) {
      const host = $("chartStage");
      if (!host || typeof LightweightCharts === "undefined") return;
      const points = (chartData && chartData.points) || [];
      if (!points.length) {
        destroyChart();
        return;
      }
      const data = seriesData(points);
      if (!tvChart) {
        tvChart = LightweightCharts.createChart(host, {
          autoSize: true,
          layout: {
            background: { color: "#0b0d11" },
            textColor: "#8b94a7",
            fontFamily: '"Segoe UI", system-ui, sans-serif',
          },
          grid: {
            vertLines: { color: "#1c2230" },
            horzLines: { color: "#1c2230" },
          },
          crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: { color: "#8b94a7", width: 1, style: 3, labelBackgroundColor: "#181c25" },
            horzLine: { color: "#8b94a7", width: 1, style: 3, labelBackgroundColor: "#181c25" },
          },
          rightPriceScale: {
            borderColor: "#262c38",
            scaleMargins: { top: 0.14, bottom: 0.22 },
          },
          timeScale: {
            borderColor: "#262c38",
            timeVisible: true,
            secondsVisible: true,
            fixLeftEdge: true,
            fixRightEdge: false,
            rightOffset: 8,
            lockVisibleTimeRangeOnResize: true,
            tickMarkFormatter: chartTick,
          },
          localization: {
            locale: "en-GB",
            timeFormatter: (time) => when(typeof time === "object" && time != null ? (time.timestamp ?? time) : time),
            priceFormatter: tokenPrice,
          },
        });
        candleSeries = tvChart.addCandlestickSeries({
          upColor: "#26a69a",
          downColor: "#ef5350",
          borderUpColor: "#26a69a",
          borderDownColor: "#ef5350",
          wickUpColor: "#26a69a",
          wickDownColor: "#ef5350",
          priceLineVisible: true,
          lastValueVisible: true,
          priceFormat: { type: "custom", minMove: 1e-12, formatter: tokenPrice },
        });
        lineSeries = tvChart.addLineSeries({
          color: "#38bdf8",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
          visible: false,
          priceFormat: { type: "custom", minMove: 1e-12, formatter: tokenPrice },
        });
        swingSeries = tvChart.addLineSeries({
          color: "rgba(224,181,106,0.9)",
          lineWidth: 1,
          lineStyle: (LightweightCharts.LineStyle && LightweightCharts.LineStyle.Dashed) || 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
          visible: false,
          priceFormat: { type: "custom", minMove: 1e-12, formatter: tokenPrice },
        });
        volumeSeries = tvChart.addHistogramSeries({
          priceFormat: { type: "volume" },
          priceScaleId: "volume",
          lastValueVisible: false,
          priceLineVisible: false,
        });
        tvChart.priceScale("volume").applyOptions({
          scaleMargins: { top: 0.82, bottom: 0 },
        });
        tvChart.subscribeCrosshairMove((param) => {
          const points = (chartData && chartData.points) || [];
          if (!param || !param.time || !candleSeries) {
            const last = points[points.length - 1];
            if (last) setOhlcLegend(last);
            return;
          }
          const candle = param.seriesData.get(candleSeries);
          const vol = volumeSeries && param.seriesData.get(volumeSeries);
          if (candle) setOhlcLegend({ ...candle, time: param.time, v_usd: vol && vol.value });
        });
        tvChart.timeScale().subscribeVisibleTimeRangeChange(onVisibleRange);
        tvChart.timeScale().subscribeVisibleLogicalRangeChange(updateWalletFirstBuyLine);
        tvChart.timeScale().subscribeSizeChange(updateWalletFirstBuyLine);
      }
      candleSeries.setData(data.candles);
      volumeSeries.setData(data.volume);
      applyStructure(points);
      if (resetView) applyVisibleRange();
      updateWalletFirstBuyLine();
      requestAnimationFrame(updateWalletFirstBuyLine);
      const last = points[points.length - 1];
      if (last) setOhlcLegend(last);
    }

    $("q").addEventListener("input", renderList);
    $("sort").addEventListener("change", renderList);
    $("wallet").addEventListener("change", () => {
      chartWallet = $("wallet").value;
      tokens = [];
      syncUrl();
      load();
    });
    $("list").addEventListener("click", (e) => {
      const row = e.target.closest(".row");
      if (!row) return;
      selected = row.dataset.addr;
      syncUrl();
      renderList();
      showDetail();
    });
    $("detail").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-copy]");
      if (!btn) return;
      try { await navigator.clipboard.writeText(btn.dataset.copy); btn.textContent = "Copied"; }
      catch { btn.textContent = "Copy failed"; }
      setTimeout(() => { btn.textContent = "Copy"; }, 1200);
    });
    $("refresh").addEventListener("click", () => refreshSelected());
    load();
  </script>
</body>
</html>
"""

def page_html() -> str:
    return (
        _PAGE_HTML
        .replace("__STRUCTURE_CONFIG__", json.dumps(structure_params()))
        .replace("__LOCAL_TIMEZONE__", json.dumps(LOCAL_TIMEZONE))
    )


PAGE_HTML = page_html()
