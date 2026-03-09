"""MedClaw - AI-powered medical research assistant."""

__version__ = "0.1.0"

from medclaw.agent.loop import AgentLoop
from medclaw.agent.skills import SkillsLoader
from medclaw.config.loader import load_config

__all__ = ["AgentLoop", "SkillsLoader", "load_config", "__version__"]
