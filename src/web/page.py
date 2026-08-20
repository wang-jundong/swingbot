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
    .refresh {
      margin-left: auto;
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
    .row.plain { grid-template-columns: 10px 1fr; }
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
      <div class="stats" id="stats"></div>
      <button class="refresh" id="refresh" type="button">Refresh</button>
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
    <div>Loading...</div>
  </div>
  <script>
    const DEX = "https://dexscreener.com/solana/";
    const GMGN = "https://gmgn.ai/sol/token/";
    const SOL = "https://solscan.io/token/";
    let tokens = [];
    let selected = null;
    let statusFilter = "all";
    let loading = false;

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
    const sol = (n) => n == null || n === "" ? "—" : num(n, 2) + " SOL";
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

    async function load() {
      if (loading) return;
      loading = true;
      $("overlay").hidden = false;
      $("refresh").disabled = true;
      try {
        const res = await fetch("/api/tokens?live=1", { cache: "no-store" });
        const data = await res.json();
        tokens = data.tokens || [];
        renderStats(data.summary || {});
        if (selected && !tokens.some(t => t.address === selected)) selected = null;
        if (!selected && tokens.length) selected = tokens[0].address;
        render();
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

    function rowPnl(t) {
      return t.status === "sold" ? t.total_pnl : t.net_pnl;
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
        if (statusFilter !== "all" && t.status !== statusFilter) return false;
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
      if (t.status === "sold") return { text: pnl(t.total_pnl), cls: cls(t.total_pnl) };
      return { text: pnl(t.net_pnl), cls: cls(t.net_pnl) };
    }

    function rowScans(t) {
      const counts = (t.scan_count || []).map(n => Number(n) || 0).filter(n => n > 0);
      if (counts.length > 1) return counts.join(" · ") + " scans";
      const n = counts.length ? counts[0] : t.scan_total;
      return (n == null ? 0 : n) + " scans";
    }

    function render() {
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
      const token = tokens.find(t => t.address === selected);
      $("detail").innerHTML = token ? detail(token) : `<div class="empty">Select a token.</div>`;
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

    $("q").addEventListener("input", render);
    $("sort").addEventListener("change", render);
    document.querySelectorAll(".pills button").forEach(btn => {
      btn.addEventListener("click", () => {
        statusFilter = btn.dataset.status;
        document.querySelectorAll(".pills button").forEach(b => b.classList.toggle("on", b === btn));
        render();
      });
    });
    $("list").addEventListener("click", (e) => {
      const row = e.target.closest(".row");
      if (!row) return;
      selected = row.dataset.addr;
      render();
    });
    $("detail").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-copy]");
      if (!btn) return;
      try { await navigator.clipboard.writeText(btn.dataset.copy); btn.textContent = "Copied"; }
      catch { btn.textContent = "Copy failed"; }
      setTimeout(() => { btn.textContent = "Copy"; }, 1200);
    });

    $("refresh").addEventListener("click", load);
    load();
  </script>
</body>
</html>
"""
