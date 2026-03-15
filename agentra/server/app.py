"""agentra FastAPI dashboard — 7-tab real-time monitoring UI."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

STATIC_DIR = Path(__file__).parent / "static"


def create_app(db_path: str | None = None) -> "FastAPI":
    if not _HAS_FASTAPI:
        raise ImportError("pip install agentra[server]")

    from agentra.db import init_db, _q
    init_db(db_path)

    app = FastAPI(title="agentra Dashboard", version="0.1.0")

    from starlette.middleware.base import BaseHTTPMiddleware

    class _SecurityHeaders(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response

    app.add_middleware(_SecurityHeaders)

    # Serve static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # WebSocket connections manager
    class ConnectionManager:
        def __init__(self):
            self.active: list[WebSocket] = []

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.active.append(ws)

        def disconnect(self, ws: WebSocket):
            if ws in self.active:
                self.active.remove(ws)

        async def broadcast(self, msg: dict):
            for ws in list(self.active):
                try:
                    await ws.send_json(msg)
                except Exception:
                    self.disconnect(ws)

    manager = ConnectionManager()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_path = STATIC_DIR / "index.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text())
        return HTMLResponse(_FALLBACK_HTML)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
        except WebSocketDisconnect:
            manager.disconnect(ws)

    def _clamp_limit(limit: int) -> int:
        return max(1, min(limit, 1000))

    def _clamp_days(days: int) -> int:
        return max(1, min(days, 365))

    # API: Security tab
    @app.get("/api/security/reports")
    async def get_security_reports(limit: int = 20):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, target_fn, model, git_commit, total_attacks, vulnerable_count, vulnerability_rate, total_cost_usd, created_at FROM red_team_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        return JSONResponse(rows)

    @app.get("/api/security/reports/{report_id}")
    async def get_report_detail(report_id: str):
        rows = _q("SELECT * FROM red_team_reports WHERE id = ?", (report_id,), db_path)
        if not rows:
            return JSONResponse({"error": "not found"}, status_code=404)
        row = rows[0]
        if row.get("results_json"):
            row["results"] = json.loads(row["results_json"])
        return JSONResponse(row)

    @app.get("/api/security/fingerprints")
    async def get_fingerprints(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q("SELECT id, models_json, plugins_json, total_cost_usd, created_at FROM fingerprints ORDER BY created_at DESC LIMIT ?", (limit,), db_path)
        for r in rows:
            r["models"] = json.loads(r["models_json"]) if r.get("models_json") else []
            r["plugins"] = json.loads(r["plugins_json"]) if r.get("plugins_json") else []
        return JSONResponse(rows)

    # API: v0.2 Security features
    @app.get("/api/security/swarm")
    async def get_swarm_reports(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, agents_json, topology, rogue_position, attacks_json, overall_trust_exploit_rate, total_cost_usd, created_at FROM swarm_scan_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        for r in rows:
            r["agents"] = json.loads(r["agents_json"]) if r.get("agents_json") else []
            r["attacks"] = json.loads(r["attacks_json"]) if r.get("attacks_json") else []
        return JSONResponse(rows)

    @app.get("/api/security/toolchain")
    async def get_toolchain_reports(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, tools_analyzed_json, find_json, total_chains_tested, high_severity_count, medium_severity_count, total_cost_usd, created_at FROM toolchain_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        for r in rows:
            r["tools_analyzed"] = json.loads(r["tools_analyzed_json"]) if r.get("tools_analyzed_json") else []
        return JSONResponse(rows)

    @app.get("/api/security/leakage")
    async def get_leakage_reports(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, target_fn, system_prompt_length, n_attempts, overall_leakage_score, technique_scores_json, total_cost_usd, created_at FROM leakage_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        for r in rows:
            r["technique_scores"] = json.loads(r["technique_scores_json"]) if r.get("technique_scores_json") else {}
        return JSONResponse(rows)

    @app.get("/api/security/multilingual")
    async def get_multilingual_reports(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, target_fn, languages_json, attacks_json, most_vulnerable_language, safest_language, total_attacks_run, total_cost_usd, created_at FROM multilingual_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        for r in rows:
            r["languages"] = json.loads(r["languages_json"]) if r.get("languages_json") else []
        return JSONResponse(rows)

    # API: Eval tab
    @app.get("/api/eval/experiments")
    async def get_experiments(limit: int = 20):
        limit = _clamp_limit(limit)
        rows = _q("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,), db_path)
        return JSONResponse(rows)

    @app.get("/api/eval/datasets")
    async def get_datasets():
        rows = _q("SELECT d.id, d.name, d.description, d.created_at, COUNT(di.id) as item_count FROM datasets d LEFT JOIN dataset_items di ON d.id = di.dataset_id GROUP BY d.id ORDER BY d.created_at DESC", db_path=db_path)
        return JSONResponse(rows)

    # API: Monitor tab
    @app.get("/api/monitor/traces")
    async def get_traces(limit: int = 50):
        limit = _clamp_limit(limit)
        rows = _q("SELECT id, name, start_time, end_time, user_id, tags, error FROM traces ORDER BY start_time DESC LIMIT ?", (limit,), db_path)
        return JSONResponse(rows)

    @app.get("/api/monitor/traces/{trace_id}/spans")
    async def get_spans(trace_id: str):
        rows = _q("SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time", (trace_id,), db_path)
        return JSONResponse(rows)

    @app.get("/api/monitor/drift")
    async def get_drift(limit: int = 10):
        limit = _clamp_limit(limit)
        rows = _q("SELECT * FROM drift_reports ORDER BY created_at DESC LIMIT ?", (limit,), db_path)
        return JSONResponse(rows)

    # API: Costs tab
    @app.get("/api/costs/summary")
    async def get_costs_summary(days: int = 7):
        days = _clamp_days(days)
        cutoff = time.time() - days * 86400
        rows = _q(
            "SELECT model, SUM(cost_usd) as total_cost, COUNT(*) as calls, AVG(duration_ms) as avg_ms FROM llm_calls WHERE timestamp > ? GROUP BY model ORDER BY total_cost DESC",
            (cutoff,), db_path
        )
        return JSONResponse(rows)

    @app.get("/api/costs/daily")
    async def get_daily_costs(days: int = 30):
        days = _clamp_days(days)
        cutoff = time.time() - days * 86400
        rows = _q(
            "SELECT DATE(timestamp, 'unixepoch') as date, SUM(cost_usd) as cost, COUNT(*) as calls FROM llm_calls WHERE timestamp > ? GROUP BY date ORDER BY date",
            (cutoff,), db_path
        )
        return JSONResponse(rows)

    # API: Review tab
    @app.get("/api/review/pending")
    async def get_pending_reviews():
        from agentra.review.annotations import ReviewQueue
        q = ReviewQueue(db_path)
        return JSONResponse(q.pending())

    @app.post("/api/review/annotate")
    async def create_annotation(body: dict):
        from agentra.review.annotations import annotate
        ann = annotate(
            result_id=body["result_id"],
            label=body["label"],
            reviewer=body.get("reviewer"),
            comment=body.get("comment"),
        )
        return JSONResponse(ann.to_json())

    # API: Compliance tab
    @app.get("/api/compliance/reports")
    async def get_compliance_reports():
        rows = _q("SELECT * FROM compliance_reports ORDER BY created_at DESC LIMIT 20", db_path=db_path)
        return JSONResponse(rows)

    @app.post("/api/compliance/generate")
    async def generate_compliance(body: dict):
        from agentra.compliance import generate_report
        report = generate_report(framework=body.get("framework", "owasp_llm_top10"))
        return JSONResponse(report.to_json())

    # API: Git tab
    @app.get("/api/git/history")
    async def get_git_history():
        rows = _q("SELECT git_commit, COUNT(*) as scans, AVG(vulnerability_rate) as avg_vuln_rate, SUM(total_cost_usd) as total_cost FROM red_team_reports WHERE git_commit IS NOT NULL GROUP BY git_commit ORDER BY MAX(created_at) DESC LIMIT 20", db_path=db_path)
        return JSONResponse(rows)

    # API: MCP scan tab (v0.3.0)
    @app.get("/api/mcp-scans")
    async def get_mcp_scans(limit: int = 20):
        rows = _q(
            "SELECT id, endpoint, total_tests, vulnerable_count, created_at FROM mcp_scan_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        return JSONResponse(rows)

    @app.get("/api/mcp-scans/{scan_id}")
    async def get_mcp_scan(scan_id: str):
        rows = _q(
            "SELECT * FROM mcp_scan_reports WHERE id = ?",
            (scan_id,), db_path
        )
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        row = rows[0]
        if row.get("results_json"):
            row["results"] = json.loads(row["results_json"])
            del row["results_json"]
        return JSONResponse(row)

    # API: Latency tab (v0.4.0)
    @app.get("/api/latency")
    async def get_latency_reports(limit: int = 20):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, fn_name, n_prompts, n_runs, p50_ms, p95_ms, p99_ms, mean_ms, min_ms, max_ms, created_at FROM latency_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        return JSONResponse(rows)

    @app.get("/api/latency/{report_id}")
    async def get_latency_report(report_id: str):
        rows = _q("SELECT * FROM latency_reports WHERE id = ?", (report_id,), db_path)
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        row = rows[0]
        if row.get("results_json"):
            row["per_prompt"] = json.loads(row["results_json"])
            del row["results_json"]
        return JSONResponse(row)

    # API: Conversation scans tab (v0.4.0)
    @app.get("/api/conversation-scans")
    async def get_conversation_scans(limit: int = 20):
        limit = _clamp_limit(limit)
        rows = _q(
            "SELECT id, fn_name, total_turns, vulnerable_count, vulnerability_rate, created_at FROM conversation_scan_reports ORDER BY created_at DESC LIMIT ?",
            (limit,), db_path
        )
        return JSONResponse(rows)

    @app.get("/api/conversation-scans/{scan_id}")
    async def get_conversation_scan(scan_id: str):
        rows = _q("SELECT * FROM conversation_scan_reports WHERE id = ?", (scan_id,), db_path)
        if not rows:
            return JSONResponse({"error": "Not found"}, status_code=404)
        row = rows[0]
        if row.get("results_json"):
            row["results"] = json.loads(row["results_json"])
            del row["results_json"]
        return JSONResponse(row)

    # Prometheus metrics endpoint (v0.4.0)
    from fastapi import Response as _FResponse

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        from agentra.monitor.prometheus import PrometheusExporter
        exp = PrometheusExporter(db_path=db_path)
        return _FResponse(
            content=exp.get_metrics_text(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return app


def run(port: int = 7234, db_path: str | None = None, no_open: bool = False) -> None:
    """Start the agentra dashboard server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError("pip install agentra[server]")

    app = create_app(db_path)

    if not no_open:
        import threading
        def _open_browser():
            import time, webbrowser
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open_browser, daemon=True).start()

    print(f"[agentra] Dashboard running at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


_FALLBACK_HTML = """<!DOCTYPE html>
<html>
<head>
<title>agentra Dashboard</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0ff; min-height: 100vh; }
.header { background: linear-gradient(135deg, #4a0080, #6a00c0); padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
.header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
.header .badge { background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.tabs { display: flex; background: #1a1a2e; border-bottom: 1px solid #2a2a4e; padding: 0 24px; overflow-x: auto; }
.tab { padding: 12px 20px; cursor: pointer; border-bottom: 2px solid transparent; color: #8888aa; font-size: 14px; transition: all 0.2s; white-space: nowrap; }
.tab.active { color: #c084fc; border-bottom-color: #c084fc; }
.tab:hover:not(.active) { color: #c084fc; }
.content { padding: 24px; }
.card { background: #1a1a2e; border: 1px solid #2a2a4e; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.card h3 { color: #c084fc; margin-bottom: 12px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
.stat { display: inline-block; margin-right: 32px; }
.stat .value { font-size: 32px; font-weight: 700; color: #e0e0ff; }
.stat .label { font-size: 12px; color: #8888aa; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; color: #8888aa; font-weight: 500; border-bottom: 1px solid #2a2a4e; }
td { padding: 10px 12px; border-bottom: 1px solid #1e1e3e; }
tr:hover td { background: #1e1e3e; }
.badge-red { background: #3d0015; color: #ff6b9d; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-green { background: #003d1a; color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-yellow { background: #3d2d00; color: #fbbf24; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
/* Loading */
.loading { text-align: center; padding: 64px; color: #8888aa; }
.spinner { width: 36px; height: 36px; border: 3px solid #2a2a4e; border-top-color: #c084fc; border-radius: 50%; animation: spin 0.75s linear infinite; margin: 0 auto 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; border-top-color: #c084fc; } }
/* Error */
.error-state { text-align: center; padding: 64px 24px; }
.error-state .error-icon { font-size: 40px; margin-bottom: 12px; }
.error-state .error-msg { color: #8888aa; font-size: 14px; margin-bottom: 20px; }
.retry-btn { background: transparent; color: #c084fc; border: 1px solid #c084fc; padding: 8px 22px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.retry-btn:hover { background: #c084fc; color: #0f0f1a; }
/* Empty states */
.empty-state { text-align: center; padding: 64px 24px; }
.empty-state .empty-icon { font-size: 44px; margin-bottom: 14px; }
.empty-state h3 { color: #c084fc; font-size: 17px; font-weight: 600; margin-bottom: 8px; }
.empty-state p { color: #8888aa; font-size: 13px; margin-bottom: 24px; }
.empty-cmd { background: #0a0a14; border: 1px solid #2a2a4e; border-radius: 6px; padding: 10px 16px; display: inline-flex; align-items: center; gap: 12px; font-family: 'Courier New', monospace; font-size: 13px; color: #c084fc; max-width: 100%; }
.copy-btn { background: #2a2a4e; color: #8888aa; border: none; padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; flex-shrink: 0; }
.copy-btn:hover { color: #e0e0ff; }
/* Chart */
.chart-wrap { position: relative; height: 220px; margin-bottom: 4px; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>agentra <span class="badge">v0.3.0</span></h1>
  </div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showTab(this,'security')">Security</div>
  <div class="tab" onclick="showTab(this,'mcp')">MCP</div>
  <div class="tab" onclick="showTab(this,'eval')">Eval</div>
  <div class="tab" onclick="showTab(this,'monitor')">Monitor</div>
  <div class="tab" onclick="showTab(this,'costs')">Costs</div>
  <div class="tab" onclick="showTab(this,'review')">Review</div>
  <div class="tab" onclick="showTab(this,'compliance')">Compliance</div>
  <div class="tab" onclick="showTab(this,'git')">Git</div>
</div>
<div class="content" id="content"></div>

<script>
const ENDPOINTS = {
  security:   '/api/security/reports',
  mcp:        '/api/mcp-scans',
  eval:       '/api/eval/experiments',
  monitor:    '/api/monitor/traces',
  costs:      '/api/costs/summary',
  review:     '/api/review/pending',
  compliance: '/api/compliance/reports',
  git:        '/api/git/history',
};

const EMPTY_STATES = {
  security:   { icon: '\\u{1F50D}', title: 'No scans yet', desc: 'Run your first red team scan to see results here.', cmd: 'agentra scan myapp:chatbot' },
  mcp:        { icon: '\\u{1F50C}', title: 'No MCP scans', desc: 'Scan an MCP server for security vulnerabilities.', cmd: 'agentra scan-mcp http://localhost:3000' },
  eval:       { icon: '\\u{1F4CA}', title: 'No experiments', desc: 'Run an evaluation experiment to compare model outputs.', cmd: 'agentra eval run experiment.py' },
  monitor:    { icon: '\\u{1F4E1}', title: 'No traces yet', desc: 'Initialize agentra to start recording production traces.', cmd: 'agentra.init()' },
  costs:      { icon: '\\u{1F4B0}', title: 'No cost data', desc: 'Initialize agentra to start tracking API costs.', cmd: 'agentra.init()' },
  review:     { icon: '\\u2705', title: 'Queue is empty', desc: 'All annotations are up to date. Nothing to review.', cmd: null },
  compliance: { icon: '\\u{1F4CB}', title: 'No compliance reports', desc: 'Generate a compliance report for your framework.', cmd: 'agentra compliance generate --framework owasp' },
  git:        { icon: '\\u{1F500}', title: 'No regression history', desc: 'Run scans across git commits to detect regressions.', cmd: null },
};

let _activeTab = 'security';
let _activeEl = null;
let _chart = null;

function copyCmd(cmd) {
  navigator.clipboard.writeText(cmd).catch(function() {});
}

function emptyState(name) {
  const s = EMPTY_STATES[name] || { icon: '\\u{1F4ED}', title: 'No data yet', desc: '', cmd: null };
  const cmdHtml = s.cmd
    ? '<div class="empty-cmd"><code>' + s.cmd + '</code><button class="copy-btn" onclick="copyCmd(\\'' + s.cmd.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'") + '\\')">Copy</button></div>'
    : '';
  return '<div class="empty-state"><div class="empty-icon">' + String.fromCodePoint(...[...s.icon].map(function(c){return c.codePointAt(0);})) + '</div><h3>' + s.title + '</h3><p>' + s.desc + '</p>' + cmdHtml + '</div>';
}

async function showTab(el, name) {
  document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
  el.classList.add('active');
  _activeTab = name;
  _activeEl = el;
  const c = document.getElementById('content');
  c.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading\u2026</p></div>';
  if (_chart) { _chart.destroy(); _chart = null; }
  try {
    const res = await fetch(ENDPOINTS[name]);
    if (!res.ok) throw new Error('HTTP ' + res.status + ' \u2014 ' + res.statusText);
    const data = await res.json();
    renderTab(name, data);
  } catch(err) {
    c.innerHTML = '<div class="error-state"><div class="error-icon">\\u26A0\\uFE0F</div><p class="error-msg">' + err.message + '</p><button class="retry-btn" onclick="showTab(_activeEl,_activeTab)">Retry</button></div>';
  }
}

function fmt(col, v) {
  if (v === null || v === undefined) return '-';
  if (col === 'created_at') return new Date(v * 1000).toLocaleString();
  if (typeof v === 'number' && col.includes('rate')) return (v * 100).toFixed(1) + '%';
  if (typeof v === 'number' && col.includes('cost')) return '$' + v.toFixed(4);
  if (typeof v === 'number' && col.includes('avg_ms')) return v.toFixed(0) + 'ms';
  if (col === 'vulnerable_count' && v > 0) return '<span class="badge-red">' + v + ' vulns</span>';
  if (col === 'status') return v === 'pass' ? '<span class="badge-green">PASS</span>' : '<span class="badge-red">FAIL</span>';
  return String(v);
}

function table(rows, cols, labels) {
  const hdrs = labels || cols;
  let h = '<table><tr>' + hdrs.map(function(c) { return '<th>' + c + '</th>'; }).join('') + '</tr>';
  for (const row of rows) {
    h += '<tr>' + cols.map(function(c) { return '<td>' + fmt(c, row[c]) + '</td>'; }).join('') + '</tr>';
  }
  return h + '</table>';
}

function barChart(id, labels, values, colors, opts) {
  opts = opts || {};
  const ctx = document.getElementById(id);
  if (!ctx) return null;
  const isHoriz = opts.horizontal;
  return new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: [{ label: opts.label || '', data: values, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      indexAxis: isHoriz ? 'y' : 'x',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { color: '#8888aa', callback: opts.xFmt || undefined }, grid: { color: '#1e1e3e' } },
        y: { beginAtZero: !isHoriz, ticks: { color: '#8888aa', callback: opts.yFmt || undefined }, grid: { color: '#1e1e3e' } }
      }
    }
  });
}

function renderTab(name, data) {
  const c = document.getElementById('content');

  if (name === 'security') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML =
      '<div class="card"><h3>Vulnerability Rate by Target</h3><div class="chart-wrap"><canvas id="ch"></canvas></div></div>' +
      '<div class="card"><h3>Red Team Reports</h3>' +
      table(rows, ['target_fn','model','total_attacks','vulnerable_count','vulnerability_rate','total_cost_usd','created_at'],
                  ['Target','Model','Attacks','Vulns','Vuln Rate','Cost','Date']) + '</div>';
    const rates = rows.map(function(r) { return +((r.vulnerability_rate || 0) * 100).toFixed(1); });
    _chart = barChart('ch',
      rows.map(function(r) { return r.target_fn || 'unknown'; }),
      rates,
      rates.map(function(r) { return r > 15 ? '#ef4444' : r > 5 ? '#f59e0b' : '#10b981'; }),
      { label: 'Vuln %', yFmt: function(v) { return v + '%'; } }
    );

  } else if (name === 'mcp') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>MCP Security Scans</h3>' +
      table(rows, ['endpoint','total_tests','vulnerable_count','created_at'], ['Endpoint','Tests','Vulns','Date']) + '</div>';

  } else if (name === 'eval') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>Experiments</h3>' +
      table(rows, ['name','fn_name','total_items','pass_rate','avg_score','total_cost_usd','created_at'],
                  ['Name','Function','Items','Pass Rate','Avg Score','Cost','Date']) + '</div>';

  } else if (name === 'monitor') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>Production Traces</h3>' +
      table(rows, ['name','status','total_duration_ms','total_cost_usd','created_at'],
                  ['Trace','Status','Duration','Cost','Date']) + '</div>';

  } else if (name === 'costs') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML =
      '<div class="card"><h3>Cost by Model</h3><div class="chart-wrap"><canvas id="ch"></canvas></div></div>' +
      '<div class="card"><h3>Breakdown</h3>' +
      table(rows, ['model','calls','total_cost','avg_ms'], ['Model','Calls','Total Cost','Avg Latency']) + '</div>';
    _chart = barChart('ch',
      rows.map(function(r) { return r.model || 'unknown'; }),
      rows.map(function(r) { return +(r.total_cost || 0).toFixed(4); }),
      '#7c3aed',
      { label: 'Cost $', horizontal: true, xFmt: function(v) { return '$' + v; } }
    );

  } else if (name === 'review') {
    const items = Array.isArray(data) ? data : (data.pending || []);
    if (!items.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>Annotation Queue</h3>' +
      table(items, ['result_id','plugin','severity','label','reviewer','created_at'],
                   ['Result ID','Plugin','Severity','Label','Reviewer','Date']) + '</div>';

  } else if (name === 'compliance') {
    const items = Array.isArray(data) ? data : [];
    if (!items.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>Compliance Reports</h3>' +
      table(items, ['framework','passed_controls','total_controls','created_at'],
                   ['Framework','Passed','Total Controls','Date']) + '</div>';

  } else if (name === 'git') {
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) { c.innerHTML = emptyState(name); return; }
    c.innerHTML = '<div class="card"><h3>Git Regression History</h3>' +
      table(rows, ['git_commit','scans','avg_vuln_rate','total_cost'],
                  ['Commit','Scans','Avg Vuln Rate','Total Cost']) + '</div>';

  } else {
    c.innerHTML = '<div class="card"><h3>' + name + '</h3><pre>' + JSON.stringify(data, null, 2) + '</pre></div>';
  }
}

// WebSocket — connect and auto-refresh active tab on updates
(function() {
  function connect() {
    try {
      const ws = new WebSocket('ws://' + location.host + '/ws');
      ws.onmessage = function(e) {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'scan_completed' || msg.type === 'refresh') {
            showTab(_activeEl, _activeTab);
          }
        } catch(_) {}
      };
      ws.onclose = function() { setTimeout(connect, 5000); };
      setInterval(function() { if (ws.readyState === 1) ws.send(JSON.stringify({type:'ping'})); }, 30000);
    } catch(_) {}
  }
  connect();
})();

// Init
(function() {
  const el = document.querySelector('.tab.active');
  _activeEl = el;
  showTab(el, 'security');
})();
</script>
</body>
</html>"""
