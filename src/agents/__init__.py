"""
CrewAI Multi-Agent Orchestration
"""
# Note: crewai_orchestrator.py was moved to deprecated/
# GrokDocCrew is available from root-level crewai_agents.py
try:
    from crewai_agents import GrokDocCrew
    __all__ = ['GrokDocCrew']
except ImportError:
    __all__ = []
