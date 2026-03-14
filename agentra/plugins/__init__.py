"""agentra.plugins — Community plugin ecosystem."""
from agentra.plugins.registry import install, list_installed, list_available, uninstall

__all__ = ["install", "list_installed", "list_available", "uninstall"]
