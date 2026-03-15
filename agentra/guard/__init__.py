"""agentra.guard — Red teaming, attack heatmap, auto-dataset, agent security, RAG security."""
from agentra.guard.red_team import red_team, RedTeamReport
from agentra.guard.fingerprint import fingerprint, ModelFingerprint
from agentra.guard.auto_dataset import auto_dataset
from agentra.guard.attacks import PLUGIN_REGISTRY
from agentra.guard.swarm import scan_swarm, SwarmScanReport
from agentra.guard.toolchain import scan_toolchain, ToolchainReport
from agentra.guard.prompt_leakage import prompt_leakage_score, LeakageReport
from agentra.guard.multilingual import scan_multilingual, MultilingualReport
from agentra.guard.mcp_scanner import scan_mcp, MCPScanReport
from agentra.guard.mcp_static import analyze_mcp_tools, ToolRiskReport
from agentra.guard.mutations import get_mutated_attacks, mutate_attack
from agentra.guard.conversation import scan_conversation, ConversationScanReport

__all__ = [
    "red_team",
    "RedTeamReport",
    "fingerprint",
    "ModelFingerprint",
    "auto_dataset",
    "PLUGIN_REGISTRY",
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
    "get_mutated_attacks",
    "mutate_attack",
    "scan_conversation",
    "ConversationScanReport",
]
