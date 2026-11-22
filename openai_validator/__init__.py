"""
OpenAI Validator — Independent Technical Review Service
Part of the NeoEve Multi-Tenant Autonomous Agent System
"""

__version__ = "1.0.0"
__author__ = "ARCHITECT Agent"

from .validator import OpenAIValidator
from .schema import ValidationInput, ValidationResult

__all__ = ["OpenAIValidator", "ValidationInput", "ValidationResult"]
