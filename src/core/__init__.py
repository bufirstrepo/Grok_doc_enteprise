"""Core Grok Doc Engine Components"""
# Note: Several core modules have been moved to deprecated/
# Only router.py remains in active use
from .router import ModelRouter

__all__ = [
    'ModelRouter',
]
