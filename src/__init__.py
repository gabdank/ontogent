"""Ontogent - AI-powered UBERON ontology term finder."""

from src.config import settings
from src.services.agent import UberonAgent

__version__ = "0.1.0"
__all__ = ["UberonAgent", "settings"]
