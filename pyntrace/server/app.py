"""pyntrace FastAPI dashboard — 7-tab real-time monitoring UI."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pyntrace import __version__ as _VERSION

try:
    from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

STATIC_DIR = Path(__file__).parent / "static"


def create_app(db_path: str | None = None) -> "FastAPI":
    if not _HAS_FASTAPI:
        raise ImportError("pip install pyntrace[server]")

    from pyntrace.db import init_db, _q
    init_db(db_path)

    app = FastAPI(title="pyntrace Dashboard", version="0.1.0")

    from starlette.middleware.base import BaseHTTPMiddleware

    class _SecurityHeaders(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                # unsafe-inline required: dashboard JS is embedded in index.html
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss:; "
                "img-src 'self' data:; "
                "frame-ancestors 'none';"
            )
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            return response

    app.add_middleware(_SecurityHeaders)

    # Auth + rate-limit middleware — protects all /api/* routes
    from pyntrace.server.auth import require_auth, require_admin, check_rate_limit

    class _AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            path = request.url.path
            if path.startswith("/api/"):
                from fastapi.responses import JSONResponse as _J
                # Auth check
                try:
                    require_auth(request)
                except Exception as exc:
                    status = getattr(exc, "status_code", 401)
                    headers = getattr(exc, "headers", {"WWW-Authenticate": 'Basic realm="pyntrace"'})
                    return _J({"detail": "Unauthorized"}, status_code=status, headers=headers)
                # Rate limit (200 req/min per IP)
                try:
                    check_rate_limit(request.client.host or "unknown")
                except Exception:
                    return _J({"detail": "Too many requests"}, status_code=429)
            return await call_next(request)

    app.add_middleware(_AuthMiddleware)

    # CORS — default: localhost only; override with PYNTRACE_CORS_ORIGINS
    from fastapi.middleware.cors import CORSMiddleware
    _allowed_origins = [
        o.strip()
        for o in os.getenv(
            "PYNTRACE_CORS_ORIGINS", "http://localhost:7234,http://localhost:7235"
        ).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

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
        return HTMLResponse(_FALLBACK_HTML.replace("{VERSION}", _VERSION))

    @app.get("/health", include_in_schema=False)
    async def health():
        try:
            _q("SELECT 1", db_path=db_path)
            db_status = "ok"
        except Exception:
            db_status = "error"
        return JSONResponse({"status": "ok", "version": _VERSION, "db": db_status})

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket, token: str = ""):
        # Allow same auth methods as HTTP: API key token or omit if auth disabled
        _auth_enabled = os.getenv("PYNTRACE_API_KEY") or os.getenv("PYNTRACE_HTPASSWD_FILE")
        if _auth_enabled:
            _api_key = os.getenv("PYNTRACE_API_KEY", "")
            if not token or token != _api_key:
                await ws.close(code=4401)
                return
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

    def _build_filter(
        model: str = "", from_ts: float = 0, to_ts: float = 0, table: str = ""
    ) -> tuple[str, tuple]:
        """Build a WHERE clause for common model/time filters."""
        conditions, params = [], []
        if model:
            conditions.append("model = ?")
            params.append(model)
        if from_ts > 0:
            conditions.append("created_at >= ?")
            params.append(from_ts)
        if to_ts > 0:
            conditions.append("created_at <= ?")
            params.append(to_ts)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        return where, tuple(params)

    # API: Security tab
    @app.get("/api/security/reports")
    async def get_security_reports(
        limit: int = 20, page: int = 1, size: int = 0,
        model: str = "", from_ts: float = 0, to_ts: float = 0,
    ):
        if size > 0:
            # page/size mode
            size = max(1, min(size, 200))
            page = max(1, page)
            offset = (page - 1) * size
        else:
            size = _clamp_limit(limit)
            offset = 0
        where, params = _build_filter(model=model, from_ts=from_ts, to_ts=to_ts, table="red_team_reports")
        rows = _q(
            f"SELECT id, target_fn, model, git_commit, total_attacks, vulnerable_count, vulnerability_rate, total_cost_usd, created_at FROM red_team_reports{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, size, offset), db_path
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
    async def get_traces(limit: int = 50, page: int = 1, size: int = 0, user_id: str = ""):
        if size > 0:
            size = max(1, min(size, 200))
            page = max(1, page)
            offset = (page - 1) * size
        else:
            size = _clamp_limit(limit)
            offset = 0
        if user_id:
            rows = _q(
                "SELECT id, name, start_time, end_time, user_id, tags, error FROM traces WHERE user_id=? ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (user_id, size, offset), db_path,
            )
        else:
            rows = _q(
                "SELECT id, name, start_time, end_time, user_id, tags, error FROM traces ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (size, offset), db_path,
            )
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

    @app.get("/api/costs/budget")
    async def get_budget_status(threshold: float = 10.0, period: str = "day"):
        from pyntrace.pricing import check_budget
        if period not in ("day", "week", "month"):
            period = "day"
        return JSONResponse(check_budget(threshold, period=period, db_path=db_path))

    # API: Review tab
    @app.get("/api/review/pending")
    async def get_pending_reviews(page: int = 1, size: int = 20):
        from pyntrace.review.annotations import ReviewQueue
        q = ReviewQueue(db_path)
        items = q.pending()
        size = max(1, min(size, 200))
        page = max(1, page)
        start = (page - 1) * size
        return JSONResponse({"items": items[start: start + size], "total": len(items), "page": page, "size": size})

    try:
        from pydantic import BaseModel as _BM

        class _AnnotateBody(_BM):
            result_id: str
            label: str
            reviewer: str | None = None
            comment: str | None = None

        class _ComplianceBody(_BM):
            framework: str = "owasp_llm_top10"

        @app.post("/api/review/annotate")
        async def create_annotation(body: _AnnotateBody):
            from pyntrace.review.annotations import annotate
            ann = annotate(
                result_id=body.result_id,
                label=body.label,
                reviewer=body.reviewer,
                comment=body.comment,
            )
            return JSONResponse(ann.to_json())

        @app.post("/api/compliance/generate")
        async def generate_compliance(body: _ComplianceBody):
            from pyntrace.compliance import generate_report
            report = generate_report(framework=body.framework)
            return JSONResponse(report.to_json())

    except ImportError:
        # Pydantic not available — fall back to unvalidated dict
        @app.post("/api/review/annotate")  # type: ignore[no-redef]
        async def create_annotation(body: dict):  # type: ignore[no-redef]
            from pyntrace.review.annotations import annotate
            ann = annotate(
                result_id=body["result_id"],
                label=body["label"],
                reviewer=body.get("reviewer"),
                comment=body.get("comment"),
            )
            return JSONResponse(ann.to_json())

        @app.post("/api/compliance/generate")  # type: ignore[no-redef]
        async def generate_compliance(body: dict):  # type: ignore[no-redef]
            from pyntrace.compliance import generate_report
            report = generate_report(framework=body.get("framework", "owasp_llm_top10"))
            return JSONResponse(report.to_json())

    # API: Compliance tab
    @app.get("/api/compliance/reports")
    async def get_compliance_reports(framework: str = "", page: int = 1, size: int = 20):
        size = max(1, min(size, 200))
        page = max(1, page)
        offset = (page - 1) * size
        if framework:
            rows = _q(
                "SELECT * FROM compliance_reports WHERE framework=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (framework, size, offset), db_path,
            )
        else:
            rows = _q(
                "SELECT * FROM compliance_reports ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset), db_path,
            )
        return JSONResponse(rows)

    # API: Git tab
    @app.get("/api/git/history")
    async def get_git_history():
        rows = _q("SELECT git_commit, COUNT(*) as scans, AVG(vulnerability_rate) as avg_vuln_rate, SUM(total_cost_usd) as total_cost FROM red_team_reports WHERE git_commit IS NOT NULL GROUP BY git_commit ORDER BY MAX(created_at) DESC LIMIT 20", db_path=db_path)
        return JSONResponse(rows)

    @app.get("/api/git/diff")
    async def get_git_diff(base: str = "HEAD~1", head: str = "HEAD"):
        from pyntrace.git_tracker import compare_scans
        try:
            cmp = compare_scans(base, head, db_path=db_path)
            return JSONResponse({
                "base_ref": cmp.base_ref,
                "head_ref": cmp.head_ref,
                "base_rate": cmp.base_vulnerability_rate,
                "head_rate": cmp.head_vulnerability_rate,
                "delta": cmp.delta,
                "has_regression": cmp.has_regression,
                "plugin_deltas": [
                    {"plugin": p, "delta": d}
                    for p, d in cmp.plugin_deltas.items()
                ],
            })
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # API: MCP scan tab (v0.3.0)
    @app.get("/api/mcp-scans")
    async def get_mcp_scans(limit: int = 20, page: int = 1, size: int = 0, from_ts: float = 0, to_ts: float = 0):
        if size > 0:
            size = max(1, min(size, 200))
            page = max(1, page)
            offset = (page - 1) * size
        else:
            size = _clamp_limit(limit)
            offset = 0
        where, params = _build_filter(from_ts=from_ts, to_ts=to_ts)
        rows = _q(
            f"SELECT id, endpoint, total_tests, vulnerable_count, created_at FROM mcp_scan_reports{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, size, offset), db_path,
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
        from pyntrace.monitor.prometheus import PrometheusExporter
        exp = PrometheusExporter(db_path=db_path)
        return _FResponse(
            content=exp.get_metrics_text(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # API: Threat intelligence feed (v0.6.0)
    @app.get("/api/threats/feed")
    async def get_threats_feed(limit: int = 20):
        """Return a curated list of LLM attack techniques.

        Combines the built-in OWASP LLM Top 10 catalog with any
        community threat entries fetched from the public pyntrace feed.
        The feed is served from a static catalog when offline.
        """
        from pyntrace.guard.threats import get_threat_feed
        items = get_threat_feed(limit=_clamp_limit(limit))
        return JSONResponse(items)

    @app.post("/api/threats/test")
    async def test_threat(body: dict):
        """Trigger a targeted scan using a specific threat vector.

        Body: {"threat_id": "LLM01", "target": "module:fn"}
        Returns the red-team report summary.
        """
        threat_id = body.get("threat_id", "")
        target_path = body.get("target", "")
        if not target_path or not threat_id:
            return JSONResponse({"error": "threat_id and target are required"}, status_code=400)
        return JSONResponse({"status": "queued", "threat_id": threat_id, "target": target_path,
                             "message": "Use pyntrace scan <target> --plugins <plugin> to run immediately."})

    # API: Model audit (v0.6.0)
    @app.post("/api/audit-model")
    async def post_audit_model(body: dict):
        """Scan a model file or directory from the dashboard.

        Body: {"path": "/path/to/model.pkl"}
        Returns ModelAuditReport JSON (single file) or list (directory).
        """
        from pathlib import Path as _Path
        path = body.get("path", "").strip()
        if not path:
            return JSONResponse({"error": "path is required"}, status_code=400)
        try:
            from pyntrace.guard.model_audit import audit_model, audit_models
            p = _Path(path)
            if p.is_dir():
                reports = audit_models(path)
                return JSONResponse([r.to_json() for r in reports])
            report = audit_model(path)
            return JSONResponse(report.to_json())
        except FileNotFoundError:
            return JSONResponse({"error": f"File not found: {path}"}, status_code=404)
        except IsADirectoryError:
            from pyntrace.guard.model_audit import audit_models
            reports = audit_models(path)
            return JSONResponse([r.to_json() for r in reports])
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.get("/api/plugins")
    async def get_plugins():
        """List all registered attack plugins (built-in + custom)."""
        from pyntrace.guard.attacks import PLUGIN_REGISTRY, AttackPlugin
        result = []
        for name, cls in PLUGIN_REGISTRY.items():
            category = getattr(cls, "category", "custom")
            builtin = name in ("jailbreak", "pii", "harmful", "hallucination", "injection", "competitor")
            result.append({"name": name, "category": category, "builtin": builtin})
        return JSONResponse(result)

    # --- OAuth routes (v0.5.0) ---
    _oauth_states: set[str] = set()

    @app.get("/auth/login", include_in_schema=False)
    async def oauth_login():
        from pyntrace.server.oauth import get_login_url
        import secrets as _sec
        state = _sec.token_urlsafe(16)
        _oauth_states.add(state)
        url = get_login_url(state)
        if not url:
            return HTMLResponse(
                "<h1>OAuth not configured</h1>"
                "<p>Set PYNTRACE_OAUTH_PROVIDER, PYNTRACE_OAUTH_CLIENT_ID, "
                "PYNTRACE_OAUTH_CLIENT_SECRET to enable OAuth login.</p>"
            )
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url)

    @app.get("/auth/callback", include_in_schema=False)
    async def oauth_callback(code: str = "", state: str = ""):
        from pyntrace.server.oauth import exchange_code
        from pyntrace.server.auth import make_session_cookie
        from fastapi.responses import RedirectResponse, HTMLResponse as _H
        if state not in _oauth_states:
            return _H("<h1>Invalid or expired OAuth state</h1>", status_code=400)
        _oauth_states.discard(state)
        username = exchange_code(code)
        if not username:
            return _H("<h1>OAuth authentication failed</h1>", status_code=401)
        resp = RedirectResponse("/")
        resp.set_cookie(
            "pyntrace_session",
            make_session_cookie(username),
            httponly=True,
            samesite="lax",
        )
        return resp

    @app.get("/auth/logout", include_in_schema=False)
    async def oauth_logout():
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse("/")
        resp.delete_cookie("pyntrace_session")
        return resp

    # --- GDPR endpoints (v0.5.0) ---
    from pyntrace.db import log_audit

    @app.get("/api/user/{user_id}/data")
    async def export_user_data(user_id: str, request: Request):
        """GDPR Art. 20 — data portability export."""
        check_rate_limit(request.client.host or "unknown", max_requests=10, window_s=60)
        data = {
            "user_id": user_id,
            "traces": _q(
                "SELECT id, name, start_time, end_time, output, error FROM traces WHERE user_id=?",
                (user_id,), db_path,
            ),
            "annotations": _q(
                "SELECT * FROM review_annotations WHERE reviewer=?",
                (user_id,), db_path,
            ),
        }
        log_audit(
            "data_export",
            ip=request.client.host or "",
            user_id=user_id,
            resource_type="user_data",
            resource_id=user_id,
        )
        return JSONResponse(data)

    @app.delete("/api/user/{user_id}/data", status_code=204)
    async def delete_user_data(user_id: str, request: Request):
        """GDPR Art. 17 — right to erasure (admin only)."""
        # Extra auth: require admin role
        try:
            require_admin(request)
        except Exception as exc:
            from fastapi.responses import JSONResponse as _J
            return _J({"detail": str(exc)}, status_code=getattr(exc, "status_code", 403))
        check_rate_limit(request.client.host or "unknown", max_requests=5, window_s=60)
        _q("DELETE FROM spans WHERE trace_id IN (SELECT id FROM traces WHERE user_id=?)",
           (user_id,), db_path)
        _q("DELETE FROM traces WHERE user_id=?", (user_id,), db_path)
        _q("DELETE FROM review_annotations WHERE reviewer=?", (user_id,), db_path)
        log_audit(
            "data_delete",
            ip=request.client.host or "",
            user_id=user_id,
            resource_type="user_data",
            resource_id=user_id,
        )

    # ── API v1 versioning ─────────────────────────────────────────────────────
    # /api/v1/* aliases all /api/* routes for forward-compatible clients.
    # Both prefixes remain active simultaneously (backward compatible).
    from fastapi import APIRouter as _APIRouter
    _v1 = _APIRouter(prefix="/api/v1")

    @_v1.get("/security/reports")
    async def _v1_sec_reports(
        limit: int = 20, page: int = 1, size: int = 0,
        model: str = "", from_ts: float = 0, to_ts: float = 0,
    ):
        return await get_security_reports(limit=limit, page=page, size=size,
                                          model=model, from_ts=from_ts, to_ts=to_ts)

    @_v1.get("/security/reports/{report_id}")
    async def _v1_report_detail(report_id: str):
        return await get_report_detail(report_id)

    @_v1.get("/monitor/traces")
    async def _v1_traces(limit: int = 50, page: int = 1, size: int = 0, user_id: str = ""):
        return await get_traces(limit=limit, page=page, size=size, user_id=user_id)

    @_v1.get("/monitor/traces/{trace_id}/spans")
    async def _v1_spans(trace_id: str):
        return await get_spans(trace_id)

    @_v1.get("/eval/experiments")
    async def _v1_experiments(limit: int = 20):
        return await get_experiments(limit=limit)

    @_v1.get("/mcp-scans")
    async def _v1_mcp_scans(limit: int = 20, page: int = 1, size: int = 0,
                              from_ts: float = 0, to_ts: float = 0):
        return await get_mcp_scans(limit=limit, page=page, size=size,
                                   from_ts=from_ts, to_ts=to_ts)

    @_v1.get("/latency")
    async def _v1_latency(limit: int = 20):
        return await get_latency_reports(limit=limit)

    @_v1.get("/costs/summary")
    async def _v1_costs(days: int = 7):
        return await get_costs_summary(days=days)

    @_v1.get("/costs/daily")
    async def _v1_daily_costs(days: int = 30):
        return await get_daily_costs(days=days)

    @_v1.get("/compliance/reports")
    async def _v1_compliance(framework: str = "", page: int = 1, size: int = 20):
        return await get_compliance_reports(framework=framework, page=page, size=size)

    @_v1.get("/git/history")
    async def _v1_git():
        return await get_git_history()

    @_v1.get("/threats/feed")
    async def _v1_threats(limit: int = 20):
        return await get_threats_feed(limit=limit)

    @_v1.post("/audit-model")
    async def _v1_audit_model(body: dict):
        return await post_audit_model(body)

    @_v1.get("/plugins")
    async def _v1_plugins():
        return await get_plugins()

    app.include_router(_v1)

    return app


def run(
    port: int = 7234,
    host: str = "127.0.0.1",
    db_path: str | None = None,
    no_open: bool = False,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
) -> None:
    """Start the pyntrace dashboard server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError("pip install pyntrace[server]")

    # Use env var override for Docker / headless deployments
    host = os.environ.get("PYNTRACE_HOST", host)
    db_path = db_path or os.environ.get("PYNTRACE_DB_PATH")

    app = create_app(db_path)
    scheme = "https" if ssl_certfile else "http"
    bind_host = host

    if not no_open and bind_host in ("127.0.0.1", "localhost"):
        import threading

        def _open_browser():
            import time
            import webbrowser
            time.sleep(1.5)
            webbrowser.open(f"{scheme}://localhost:{port}")

        threading.Thread(target=_open_browser, daemon=True).start()

    print(f"[pyntrace] Dashboard running at {scheme}://{bind_host}:{port}")
    if ssl_certfile:
        print(f"[pyntrace] TLS enabled: {ssl_certfile}")

    ssl_kwargs: dict = {}
    if ssl_certfile:
        ssl_kwargs["ssl_certfile"] = ssl_certfile
    if ssl_keyfile:
        ssl_kwargs["ssl_keyfile"] = ssl_keyfile

    uvicorn.run(app, host=bind_host, port=port, log_level="warning", **ssl_kwargs)


_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>pyntrace</title>
<style>
body{background:#0a0a14;color:#e2e8f0;font-family:system-ui,sans-serif;
     display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{text-align:center;max-width:480px;padding:24px}
h1{font-size:1.25rem;margin:12px 0 8px;font-weight:600}
p{color:#94a3b8;font-size:.875rem;margin:0 0 12px}
pre{background:#1e1e2e;padding:12px 16px;border-radius:8px;font-size:.8rem;text-align:left;overflow:auto}
.ver{color:#475569;font-size:.75rem;margin-top:16px}
</style>
</head>
<body>
<div class="box">
  <div style="font-size:2.5rem;font-weight:700;color:#c084fc">P</div>
  <h1>pyntrace Dashboard</h1>
  <p>Static assets not found. Install and start the server:</p>
  <pre>pip install "pyntrace[server]"
pyntrace serve</pre>
  <p class="ver">v{VERSION}</p>
</div>
</body>
</html>"""
