"""
agentra — Red-team, eval, and monitor your LLMs. Security-first, Python-native.

Quick start:
    import agentra
    agentra.init()

    # Red team your chatbot
    report = agentra.red_team(my_chatbot, plugins=["jailbreak", "pii"])
    report.summary()

    # Attack heatmap across models
    fp = agentra.guard.fingerprint({"gpt-4o-mini": fn1, "claude-haiku": fn2})
    fp.heatmap()

    # Auto-generate test cases
    ds = agentra.auto_dataset(my_chatbot, n=50, focus="adversarial")
"""
from __future__ import annotations

__version__ = "0.5.0"
__author__ = "agentra"

# Guard (primary — security)
from agentra.guard.red_team import red_team, RedTeamReport
from agentra.guard.fingerprint import fingerprint, ModelFingerprint
from agentra.guard.auto_dataset import auto_dataset
from agentra.guard.swarm import scan_swarm, SwarmScanReport
from agentra.guard.toolchain import scan_toolchain, ToolchainReport
from agentra.guard.prompt_leakage import prompt_leakage_score, LeakageReport
from agentra.guard.multilingual import scan_multilingual, MultilingualReport
from agentra.guard.mcp_scanner import scan_mcp, MCPScanReport
from agentra.guard.mcp_static import analyze_mcp_tools, ToolRiskReport
from agentra.guard.conversation import scan_conversation, ConversationScanReport

# Eval
from agentra.eval.dataset import Dataset, DatasetItem
from agentra.eval.experiment import Experiment, ExperimentResults
from agentra.eval import scorers
from agentra.eval.compare import compare_models, prompt_ab_test

# Monitor
from agentra.monitor.tracer import trace, span
from agentra.monitor.drift import DriftDetector, DriftReport
from agentra.monitor.alerts import AlertManager, AlertRule
from agentra.monitor.prometheus import PrometheusExporter, expose_metrics
from agentra.monitor.latency import benchmark_latency, LatencyReport

# Sub-packages
from agentra import guard, eval, monitor

__all__ = [
    # Core
    "init",
    "dataset",
    "experiment",
    # Guard
    "red_team",
    "RedTeamReport",
    "fingerprint",
    "ModelFingerprint",
    "auto_dataset",
    "scan_swarm",
    "SwarmScanReport",
    "scan_toolchain",
    "ToolchainReport",
    "prompt_leakage_score",
    "LeakageReport",
    "scan_multilingual",
    "MultilingualReport",
    "scan_mcp",
    "MCPScanReport",
    "analyze_mcp_tools",
    "ToolRiskReport",
    "scan_conversation",
    "ConversationScanReport",
    "guard",
    # Eval
    "Dataset",
    "DatasetItem",
    "Experiment",
    "ExperimentResults",
    "scorers",
    "compare_models",
    "prompt_ab_test",
    "eval",
    # Monitor
    "trace",
    "span",
    "DriftDetector",
    "DriftReport",
    "AlertManager",
    "AlertRule",
    "PrometheusExporter",
    "expose_metrics",
    "benchmark_latency",
    "LatencyReport",
    "monitor",
]


def init(
    persist: bool = True,
    db_path: str | None = None,
    offline: bool = False,
    local_judge_model: str = "llama3",
    judge_model: str = "gpt-4o-mini",
) -> None:
    """
    Initialize agentra — enable persistence and activate SDK interceptors.

    Args:
        persist: write results to SQLite (default True)
        db_path: custom path for agentra.db (default: ~/.agentra/data.db)
        offline: use local Ollama model for judging (no external API calls)
        local_judge_model: Ollama model to use when offline=True
        judge_model: default judge model when offline=False

    Example:
        agentra.init()                              # Standard
        agentra.init(offline=True)                  # Fully offline with Ollama
        agentra.init(db_path="/tmp/agentra.db")     # Custom DB path
    """
    from agentra import providers, db

    # Load local secrets file (no-op if ~/.agentra/secrets.json doesn't exist)
    try:
        from agentra.secrets.store import load_secrets
        load_secrets()
    except Exception:
        pass

    # Configure providers
    providers.configure(
        offline=offline,
        local_judge_model=local_judge_model,
        judge_model=judge_model,
    )

    # Configure DB path
    if db_path:
        db.set_db_path(db_path)

    # Initialize DB schema
    if persist:
        db.init_db(db_path)

    # Activate SDK interceptors
    try:
        from agentra import interceptor
        interceptor.activate()
    except Exception:
        pass


def dataset(name: str, description: str = "") -> Dataset:
    """Create or load a named dataset."""
    return Dataset(name, description)


def experiment(
    name: str,
    dataset: Dataset | str,
    fn,
    scorers: list | None = None,
) -> Experiment:
    """Create an experiment."""
    return Experiment(name=name, dataset=dataset, fn=fn, scorers=scorers or [])
