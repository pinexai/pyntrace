"""agentra CLI — command-line interface for red teaming, eval, monitoring, and more."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Callable


def _load_fn(module_path: str) -> Callable:
    """Load a function from 'module:function' syntax."""
    if ":" not in module_path:
        print(f"[agentra] Error: expected 'module:function' format, got '{module_path}'")
        sys.exit(1)
    module_name, fn_name = module_path.rsplit(":", 1)
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, fn_name)
    except (ImportError, AttributeError) as e:
        print(f"[agentra] Error loading {module_path}: {e}")
        sys.exit(1)


def cmd_scan(args) -> None:
    """agentra scan module:fn [--plugins ...] [--n 10] [--git-compare main] [--fail-on-regression]"""
    from agentra import init, red_team
    init(persist=True)

    fn = _load_fn(args.target)

    # --fast: quick CI mode (5 attacks, jailbreak+harmful only)
    if getattr(args, "fast", False):
        plugins = ["jailbreak", "harmful"]
        args.n = 5
    # --critical-only: only high-severity plugins
    elif getattr(args, "critical_only", False):
        plugins = ["jailbreak", "harmful"]
    else:
        plugins = [p.strip() for p in args.plugins.split(",")] if args.plugins else ["jailbreak", "pii", "harmful"]

    report = red_team(
        fn,
        plugins=plugins,
        n_attacks=args.n,
        git_compare=args.git_compare,
        fail_on_regression=args.fail_on_regression,
        max_cost_usd=args.max_cost,
    )
    report.summary()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_json(), f, indent=2)
        print(f"[agentra] Report saved to {args.output}")

    if args.output_sarif:
        report.save_sarif(args.output_sarif)

    if args.output_junit:
        report.save_junit(args.output_junit)


def cmd_benchmark(args) -> None:
    """agentra benchmark module:fn --prompts prompts.txt [--n-runs 3]"""
    from agentra import init
    from agentra.monitor.latency import benchmark_latency
    init(persist=True)

    fn = _load_fn(args.target)

    if args.prompts:
        with open(args.prompts) as f:
            prompts = [line.strip() for line in f if line.strip()]
    else:
        prompts = [
            "Hello, how are you?",
            "What is the capital of France?",
            "Explain quantum computing in one sentence.",
            "Write a haiku about the ocean.",
            "What is 2 + 2?",
        ]

    report = benchmark_latency(fn, prompts=prompts, n_runs=args.n_runs, warmup=args.warmup)
    report.summary()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_json(), f, indent=2)
        print(f"[agentra] Latency report saved to {args.output}")


def cmd_scan_conversation(args) -> None:
    """agentra scan-conversation module:fn [--n 20]"""
    from agentra import init
    from agentra.guard.conversation import scan_conversation
    init(persist=True)

    fn = _load_fn(args.target)
    report = scan_conversation(fn, n=args.n)
    report.summary()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_json(), f, indent=2)
        print(f"[agentra] Report saved to {args.output}")


def cmd_fingerprint(args) -> None:
    """agentra fingerprint module:fn1 module:fn2 [--plugins all] [--n 10]"""
    from agentra import init
    from agentra.guard.fingerprint import fingerprint
    init(persist=True)

    targets = {}
    for t in args.targets:
        fn = _load_fn(t)
        targets[t] = fn

    plugins = [p.strip() for p in args.plugins.split(",")] if args.plugins else ["jailbreak", "pii", "harmful", "hallucination", "injection"]
    if args.plugins == "all":
        from agentra.guard.attacks import PLUGIN_REGISTRY
        plugins = list(PLUGIN_REGISTRY.keys())

    fp = fingerprint(targets, plugins=plugins, n_attacks=args.n)
    fp.heatmap()


def cmd_auto_dataset(args) -> None:
    """agentra auto-dataset module:fn [--n 20] [--focus adversarial] [--name myds]"""
    from agentra import init, auto_dataset
    init(persist=True)

    fn = _load_fn(args.target)
    ds = auto_dataset(fn, n=args.n, focus=args.focus, name=args.name)
    print(f"[agentra] Generated dataset '{ds.name}' with {len(ds)} items")


def cmd_scan_agent(args) -> None:
    from agentra import init
    from agentra.guard.agent import scan_agent
    init(persist=True)

    fn = _load_fn(args.target)
    report = scan_agent(fn, mcp_endpoint=args.mcp)
    report.summary()


def cmd_scan_rag(args) -> None:
    from agentra import init
    from agentra.guard.rag_scanner import scan_rag
    import os
    init(persist=True)

    # Load documents
    docs = []
    if os.path.isdir(args.docs):
        for f in os.listdir(args.docs):
            fp = os.path.join(args.docs, f)
            if os.path.isfile(fp):
                with open(fp, errors="replace") as fh:
                    docs.append({"id": f, "content": fh.read()})
    else:
        with open(args.docs, errors="replace") as fh:
            docs = [{"id": args.docs, "content": fh.read()}]

    system_prompt = None
    if args.system_prompt:
        with open(args.system_prompt) as fh:
            system_prompt = fh.read()

    report = scan_rag(docs, system_prompt=system_prompt, baseline_hash=args.baseline_hash)
    report.summary()


def cmd_scan_swarm(args) -> None:
    from agentra import init
    from agentra.guard.swarm import scan_swarm
    init(persist=True)

    # Load agents dict: --agents "module:fn1,module:fn2" with optional names
    agents = {}
    for spec in args.agents.split(","):
        spec = spec.strip()
        if "=" in spec:
            name, target = spec.split("=", 1)
            agents[name.strip()] = _load_fn(target.strip())
        else:
            fn = _load_fn(spec)
            agents[fn.__name__] = fn

    attacks = [a.strip() for a in args.attacks.split(",")] if args.attacks else None
    kwargs = dict(topology=args.topology, n_attacks=args.n)
    if args.rogue:
        kwargs["rogue_position"] = args.rogue
    if attacks:
        kwargs["attacks"] = attacks

    report = scan_swarm(agents, **kwargs)
    report.summary()
    report.propagation_graph()


def cmd_scan_toolchain(args) -> None:
    from agentra import init
    from agentra.guard.toolchain import scan_toolchain
    init(persist=True)

    agent_fn = _load_fn(args.target)
    tools = [_load_fn(t.strip()) for t in args.tools.split(",")]
    find = [f.strip() for f in args.find.split(",")] if args.find else None
    kwargs = {"max_chain_depth": args.depth}
    if find:
        kwargs["find"] = find

    report = scan_toolchain(agent_fn, tools, **kwargs)
    report.summary()


def cmd_scan_prompt_leakage(args) -> None:
    from agentra import init
    from agentra.guard.prompt_leakage import prompt_leakage_score
    init(persist=True)

    fn = _load_fn(args.target)
    with open(args.system_prompt) as fh:
        system_prompt = fh.read()

    techniques = [t.strip() for t in args.techniques.split(",")] if args.techniques else None
    kwargs = {"n_attempts": args.n}
    if techniques:
        kwargs["techniques"] = techniques

    report = prompt_leakage_score(fn, system_prompt, **kwargs)
    report.summary()


def cmd_scan_multilingual(args) -> None:
    from agentra import init
    from agentra.guard.multilingual import scan_multilingual
    init(persist=True)

    fn = _load_fn(args.target)
    languages = [lang.strip() for lang in args.languages.split(",")] if args.languages else None
    attacks = [a.strip() for a in args.attacks.split(",")] if args.attacks else None
    kwargs = {"n_attacks": args.n}
    if languages:
        kwargs["languages"] = languages
    if attacks:
        kwargs["attacks"] = attacks

    report = scan_multilingual(fn, **kwargs)
    report.summary()
    report.heatmap()


def cmd_scan_mcp(args) -> None:
    from agentra import init
    from agentra.guard.mcp_scanner import scan_mcp
    init(persist=True)

    tests = [t.strip() for t in args.tests.split(",")] if args.tests and args.tests != "all" else "all"
    report = scan_mcp(
        endpoint=args.endpoint,
        tests=tests,
        auth_token=args.auth_token,
        timeout=args.timeout,
    )
    report.summary()

    if args.output_sarif:
        report.save_sarif(args.output_sarif)
    if args.output_junit:
        report.save_junit(args.output_junit)
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(report.to_json(), f, indent=2)
        print(f"[agentra] JSON report saved to {args.output}")


def cmd_analyze_mcp_tools(args) -> None:
    import json
    from agentra.guard.mcp_static import analyze_mcp_tools

    with open(args.file) as f:
        tools = json.load(f)

    if not isinstance(tools, list):
        # Handle {tools: [...]} wrapper format
        tools = tools.get("tools", tools)

    report = analyze_mcp_tools(tools)
    report.summary()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_json(), f, indent=2)
        print(f"[agentra] JSON report saved to {args.output}")


def cmd_eval_run(args) -> None:
    from agentra import init
    init(persist=True)

    # Load experiment file
    import runpy
    print(f"[agentra] Running eval script: {args.file} — ensure you trust this file.")
    ns = runpy.run_path(args.file)
    exp = ns.get("experiment") or ns.get("exp")
    if exp is None:
        print("[agentra] Error: file must define 'experiment' or 'exp' variable")
        sys.exit(1)

    results = exp.run()
    results.summary()

    if args.fail_below and results.pass_rate < args.fail_below:
        print(f"[agentra] FAIL: pass rate {results.pass_rate:.1%} < {args.fail_below:.1%}")
        sys.exit(1)


def cmd_monitor_watch(args) -> None:
    from agentra import init
    from agentra.monitor.daemon import watch
    init(persist=True)

    fn = _load_fn(args.target)
    plugins = [p.strip() for p in args.plugins.split(",")] if args.plugins else ["jailbreak", "pii"]
    watch(fn, interval_seconds=args.interval, plugins=plugins, n_attacks=args.n, alert_webhook=args.webhook)


def cmd_monitor_drift(args) -> None:
    from agentra import init
    from agentra.monitor.drift import DriftDetector
    init(persist=True)

    detector = DriftDetector(on_drift="warn" if not args.fail else "raise")
    detector.baseline(args.baseline)
    report = detector.check(window_hours=args.window)
    report.summary()


def cmd_monitor_traces(args) -> None:
    from agentra.db import _q
    rows = _q("SELECT id, name, start_time, end_time, user_id, error FROM traces ORDER BY start_time DESC LIMIT ?", (args.limit,))
    if not rows:
        print("[agentra] No traces found.")
        return
    print(f"\n{'ID':^38} {'Name':<25} {'Start':^20} {'Error'}")
    print("-" * 90)
    import datetime
    for r in rows:
        ts = datetime.datetime.fromtimestamp(r["start_time"]).strftime("%Y-%m-%d %H:%M:%S") if r["start_time"] else "-"
        print(f"{r['id']:<38} {(r['name'] or '-'):<25} {ts:<20} {r['error'] or '-'}")


def cmd_review_list(args) -> None:
    from agentra.review.annotations import ReviewQueue
    q = ReviewQueue()
    if args.pending:
        items = q.pending()
        print(f"\n[agentra] {len(items)} pending review items:")
        for item in items[:20]:
            print(f"  [{item['plugin']}] {item['attack_input'][:80]}...")
    else:
        anns = q.list_annotations(limit=args.limit)
        print(f"\n[agentra] {len(anns)} annotations:")
        for a in anns:
            print(f"  [{a.label}] {a.result_id[:40]} — {a.comment or ''}")


def cmd_review_annotate(args) -> None:
    from agentra.review.annotations import annotate
    ann = annotate(args.result_id, args.label, reviewer=args.reviewer, comment=args.comment)
    print(f"[agentra] Annotated {ann.result_id} as '{ann.label}'")


def cmd_compliance(args) -> None:
    from agentra import init
    from agentra.compliance import generate_report
    init(persist=True)

    for framework in args.framework:
        report = generate_report(framework, output=args.output)
        report.summary()


def cmd_plugin_list(args) -> None:
    from agentra.plugins import list_available, list_installed
    print("\n[agentra] Available plugins:")
    for p in list_available():
        print(f"  {p['name']:<30} {p['description']}")
    print("\n[agentra] Installed plugins:")
    for p in list_installed():
        print(f"  {p['name']:<30} v{p.get('version', '?')}")


def cmd_plugin_install(args) -> None:
    from agentra.plugins import install
    install(args.name)


def cmd_serve(args) -> None:
    from agentra.server.app import run
    run(port=args.port, db_path=args.db, no_open=args.no_open)


def cmd_history(args) -> None:
    from agentra.db import _q, init_db
    init_db()
    rows = _q("SELECT target_fn, model, vulnerability_rate, total_cost_usd, created_at FROM red_team_reports ORDER BY created_at DESC LIMIT ?", (args.limit,))
    if not rows:
        print("[agentra] No scan history found. Run agentra scan first.")
        return
    import datetime
    print(f"\n{'Target':<30} {'Model':<15} {'Vuln%':>8} {'Cost':>10} {'Date'}")
    print("-" * 75)
    for r in rows:
        ts = datetime.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d") if r["created_at"] else "-"
        rate = f"{r['vulnerability_rate']:.1%}" if r["vulnerability_rate"] is not None else "-"
        cost = f"${r['total_cost_usd']:.4f}" if r["total_cost_usd"] else "-"
        print(f"{(r['target_fn'] or '-'):<30} {(r['model'] or '-'):<15} {rate:>8} {cost:>10} {ts}")


def cmd_costs(args) -> None:
    from agentra.db import _q, init_db
    import time
    init_db()
    cutoff = time.time() - args.days * 86400
    rows = _q("SELECT model, SUM(cost_usd) as total, COUNT(*) as calls FROM llm_calls WHERE timestamp > ? GROUP BY model ORDER BY total DESC", (cutoff,))
    if not rows:
        print(f"[agentra] No LLM calls in the last {args.days} days.")
        return
    print(f"\nLLM Costs — last {args.days} days:")
    print(f"  {'Model':<30} {'Calls':>8} {'Total Cost':>12}")
    print("  " + "-" * 54)
    total = 0.0
    for r in rows:
        print(f"  {r['model']:<30} {r['calls']:>8} ${r['total']:>11.4f}")
        total += r["total"]
    print(f"\n  {'TOTAL':<30} {'':>8} ${total:>11.4f}")


def cmd_version(args) -> None:
    from agentra import __version__
    print(f"agentra v{__version__}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agentra",
        description="Red-team, eval, and monitor your LLMs.",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Red team a function")
    p_scan.add_argument("target", help="module:function")
    p_scan.add_argument("--plugins", default="jailbreak,pii,harmful")
    p_scan.add_argument("--n", type=int, default=10, help="Attacks per plugin")
    p_scan.add_argument("--git-compare", dest="git_compare", metavar="REF")
    p_scan.add_argument("--fail-on-regression", action="store_true", dest="fail_on_regression")
    p_scan.add_argument("--max-cost", dest="max_cost", type=float, default=None, metavar="USD",
                        help="Abort scan if total LLM cost exceeds this amount (e.g. 5.00)")
    p_scan.add_argument("--output", metavar="FILE", help="Save JSON report to file")
    p_scan.add_argument("--output-sarif", dest="output_sarif", metavar="FILE",
                        help="Save SARIF 2.1.0 report (GitHub Advanced Security)")
    p_scan.add_argument("--output-junit", dest="output_junit", metavar="FILE",
                        help="Save JUnit XML report (CI test reporters)")
    p_scan.add_argument("--fast", action="store_true",
                        help="Quick CI mode: n=5, jailbreak+harmful only (<1 min)")
    p_scan.add_argument("--critical-only", action="store_true", dest="critical_only",
                        help="Only high-severity plugins (jailbreak, harmful)")
    p_scan.set_defaults(func=cmd_scan)

    # fingerprint
    p_fp = sub.add_parser("fingerprint", help="Attack heatmap across models")
    p_fp.add_argument("targets", nargs="+", help="module:function pairs")
    p_fp.add_argument("--plugins", default="jailbreak,pii,harmful")
    p_fp.add_argument("--n", type=int, default=10)
    p_fp.set_defaults(func=cmd_fingerprint)

    # auto-dataset
    p_ds = sub.add_parser("auto-dataset", help="Generate test dataset from function")
    p_ds.add_argument("target", help="module:function")
    p_ds.add_argument("--n", type=int, default=20)
    p_ds.add_argument("--focus", default="mixed", choices=["adversarial", "normal", "edge_case", "mixed"])
    p_ds.add_argument("--name")
    p_ds.set_defaults(func=cmd_auto_dataset)

    # scan-agent
    p_agent = sub.add_parser("scan-agent", help="Test agentic workflow security")
    p_agent.add_argument("target", help="module:function")
    p_agent.add_argument("--mcp", metavar="URL")
    p_agent.set_defaults(func=cmd_scan_agent)

    # scan-rag
    p_rag = sub.add_parser("scan-rag", help="Scan RAG corpus for poisoning and PII")
    p_rag.add_argument("--docs", required=True, metavar="PATH")
    p_rag.add_argument("--system-prompt", dest="system_prompt", metavar="FILE")
    p_rag.add_argument("--baseline-hash", dest="baseline_hash", metavar="HASH")
    p_rag.set_defaults(func=cmd_scan_rag)

    # scan-swarm
    p_swarm = sub.add_parser("scan-swarm", help="Test multi-agent trust exploitation")
    p_swarm.add_argument("--agents", required=True, metavar="SPECS",
                         help="Comma-separated module:fn specs, optionally name=module:fn")
    p_swarm.add_argument("--topology", default="chain",
                         choices=["chain", "star", "mesh", "hierarchical"])
    p_swarm.add_argument("--rogue", metavar="AGENT_NAME")
    p_swarm.add_argument("--attacks", metavar="TYPES",
                         help="Comma-separated: payload_relay,privilege_escalation,memory_poisoning")
    p_swarm.add_argument("--n", type=int, default=5, metavar="N")
    p_swarm.set_defaults(func=cmd_scan_swarm)

    # scan-toolchain
    p_tc = sub.add_parser("scan-toolchain", help="Map tool-chain privilege escalation paths")
    p_tc.add_argument("target", metavar="AGENT", help="module:agent_fn")
    p_tc.add_argument("--tools", required=True, metavar="SPECS",
                      help="Comma-separated module:tool_fn specs")
    p_tc.add_argument("--find", metavar="RISKS",
                      help="Comma-separated: data_exfiltration,privilege_escalation,unauthorized_writes")
    p_tc.add_argument("--depth", type=int, default=4, metavar="N")
    p_tc.set_defaults(func=cmd_scan_toolchain)

    # scan-prompt-leakage
    p_leak = sub.add_parser("scan-prompt-leakage", help="Score system prompt leakage resistance")
    p_leak.add_argument("target", metavar="FN", help="module:chatbot_fn")
    p_leak.add_argument("--system-prompt", dest="system_prompt", required=True, metavar="FILE")
    p_leak.add_argument("--n", type=int, default=50, metavar="N")
    p_leak.add_argument("--techniques", metavar="LIST",
                        help="Comma-separated: direct,indirect,behavioral_inference,jailbreak")
    p_leak.set_defaults(func=cmd_scan_prompt_leakage)

    # scan-multilingual
    p_ml = sub.add_parser("scan-multilingual", help="Cross-language safety bypass heatmap")
    p_ml.add_argument("target", metavar="FN", help="module:chatbot_fn")
    p_ml.add_argument("--languages", metavar="LANGS", help="Comma-separated ISO codes: en,zh,ar,sw")
    p_ml.add_argument("--attacks", metavar="PLUGINS", help="Comma-separated: jailbreak,harmful")
    p_ml.add_argument("--n", type=int, default=5, metavar="N")
    p_ml.set_defaults(func=cmd_scan_multilingual)

    # scan-mcp
    p_mcp = sub.add_parser("scan-mcp", help="Scan a live MCP server for security vulnerabilities")
    p_mcp.add_argument("endpoint", metavar="URL", help="MCP server URL (e.g. http://localhost:3000)")
    p_mcp.add_argument("--tests", metavar="LIST",
                       help="Comma-separated test names or 'all' (default: all)", default="all")
    p_mcp.add_argument("--auth-token", dest="auth_token", metavar="TOKEN",
                       help="Bearer token for authenticated MCP servers")
    p_mcp.add_argument("--timeout", type=int, default=10, metavar="SECS")
    p_mcp.add_argument("--output", metavar="FILE", help="Save JSON report to file")
    p_mcp.add_argument("--output-sarif", dest="output_sarif", metavar="FILE",
                       help="Save SARIF 2.1.0 report (GitHub Advanced Security)")
    p_mcp.add_argument("--output-junit", dest="output_junit", metavar="FILE",
                       help="Save JUnit XML report (CI test reporters)")
    p_mcp.set_defaults(func=cmd_scan_mcp)

    # analyze-mcp-tools
    p_mcp_static = sub.add_parser("analyze-mcp-tools", help="Static analysis of MCP tool schemas")
    p_mcp_static.add_argument("file", metavar="TOOLS_JSON",
                              help="JSON file with MCP tool definitions (list of {name, description})")
    p_mcp_static.add_argument("--output", metavar="FILE", help="Save JSON report to file")
    p_mcp_static.set_defaults(func=cmd_analyze_mcp_tools)

    # eval run
    p_eval = sub.add_parser("eval", help="Evaluation commands")
    eval_sub = p_eval.add_subparsers(dest="eval_command")
    p_eval_run = eval_sub.add_parser("run")
    p_eval_run.add_argument("file", help="Python file defining 'experiment' variable")
    p_eval_run.add_argument("--fail-below", type=float, dest="fail_below", metavar="RATE")
    p_eval_run.set_defaults(func=cmd_eval_run)

    # monitor
    p_mon = sub.add_parser("monitor", help="Monitoring commands")
    mon_sub = p_mon.add_subparsers(dest="mon_command")

    p_watch = mon_sub.add_parser("watch")
    p_watch.add_argument("target", help="module:function")
    p_watch.add_argument("--interval", type=int, default=60)
    p_watch.add_argument("--plugins", default="jailbreak,pii")
    p_watch.add_argument("--n", type=int, default=5)
    p_watch.add_argument("--webhook", metavar="URL")
    p_watch.set_defaults(func=cmd_monitor_watch)

    p_drift = mon_sub.add_parser("drift")
    p_drift.add_argument("--baseline", required=True, metavar="EXP_NAME")
    p_drift.add_argument("--window", type=float, default=24.0, metavar="HOURS")
    p_drift.add_argument("--fail", action="store_true")
    p_drift.set_defaults(func=cmd_monitor_drift)

    p_traces = mon_sub.add_parser("traces")
    p_traces.add_argument("--limit", type=int, default=20)
    p_traces.set_defaults(func=cmd_monitor_traces)

    # review
    p_rev = sub.add_parser("review", help="Human review workflow")
    rev_sub = p_rev.add_subparsers(dest="rev_command")

    p_rev_list = rev_sub.add_parser("list")
    p_rev_list.add_argument("--pending", action="store_true")
    p_rev_list.add_argument("--limit", type=int, default=20)
    p_rev_list.set_defaults(func=cmd_review_list)

    p_rev_ann = rev_sub.add_parser("annotate")
    p_rev_ann.add_argument("result_id")
    p_rev_ann.add_argument("--label", required=True, choices=["true_positive", "false_positive", "needs_review"])
    p_rev_ann.add_argument("--reviewer")
    p_rev_ann.add_argument("--comment")
    p_rev_ann.set_defaults(func=cmd_review_annotate)

    # compliance
    p_comp = sub.add_parser("compliance", help="Generate compliance reports")
    p_comp.add_argument("--framework", action="append", default=[], dest="framework",
                        choices=["owasp_llm_top10", "nist_ai_rmf", "eu_ai_act", "soc2"],
                        help="Framework to report on (can specify multiple)")
    p_comp.add_argument("--output", metavar="FILE")
    p_comp.set_defaults(func=cmd_compliance, framework=["owasp_llm_top10"])

    # plugin
    p_plug = sub.add_parser("plugin", help="Plugin ecosystem")
    plug_sub = p_plug.add_subparsers(dest="plug_command")
    plug_sub.add_parser("list").set_defaults(func=cmd_plugin_list)
    p_install = plug_sub.add_parser("install")
    p_install.add_argument("name")
    p_install.set_defaults(func=cmd_plugin_install)

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Latency profiling (p50/p95/p99)")
    p_bench.add_argument("target", help="module:function")
    p_bench.add_argument("--prompts", metavar="FILE", help="Text file with one prompt per line")
    p_bench.add_argument("--n-runs", dest="n_runs", type=int, default=3, metavar="N",
                         help="Timed runs per prompt (default 3)")
    p_bench.add_argument("--warmup", type=int, default=1, metavar="N",
                         help="Discarded warm-up runs per prompt (default 1)")
    p_bench.add_argument("--output", metavar="FILE", help="Save JSON report to file")
    p_bench.set_defaults(func=cmd_benchmark)

    # scan-conversation
    p_conv = sub.add_parser("scan-conversation", help="Multi-turn conversation attack scanner")
    p_conv.add_argument("target", help="module:function (must accept list[dict])")
    p_conv.add_argument("--n", type=int, default=20, metavar="N",
                        help="Number of multi-turn attacks to run (default 20)")
    p_conv.add_argument("--output", metavar="FILE", help="Save JSON report to file")
    p_conv.set_defaults(func=cmd_scan_conversation)

    # serve
    p_serve = sub.add_parser("serve", help="Start dashboard")
    p_serve.add_argument("--port", type=int, default=7234)
    p_serve.add_argument("--db", metavar="PATH")
    p_serve.add_argument("--no-open", action="store_true", dest="no_open")
    p_serve.set_defaults(func=cmd_serve)

    # history / costs / version
    p_hist = sub.add_parser("history", help="Show scan history")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.set_defaults(func=cmd_history)

    p_costs = sub.add_parser("costs", help="Show LLM costs")
    p_costs.add_argument("--days", type=int, default=7)
    p_costs.set_defaults(func=cmd_costs)

    sub.add_parser("version").set_defaults(func=cmd_version)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
