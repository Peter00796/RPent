"""LIBERO prompt bundle assembly."""

from __future__ import annotations

from robots.libero.prompts import system as system_parts
from robots.libero.prompts import user as user_parts
from rpent.context.prompt_utils import Numbered, PromptNode


def system_prompt() -> PromptNode:
    """Assemble the LIBERO system prompt tree."""
    return {
        "ROLE AND EVALUATION": system_parts.ROLE_AND_EVALUATION,
        "EVIDENCE DISCIPLINE (NON-NEGOTIABLE)": system_parts.EVIDENCE_DISCIPLINE,
        "MECHANICS NO TOOL REPORTS": system_parts.MECHANICS,
        "RUNTIME": system_parts.RUNTIME,
        "YOUR GOAL": system_parts.GOAL,
        "RULES (NON-NEGOTIABLE)": system_parts.RULES,
        "LOCALIZATION — four channels, and which question each answers": (
            system_parts.LOCALIZATION
        ),
        "PERCEPTION PASS — agentview = IDENTITY, wrist = GEOMETRY": (
            system_parts.PERCEPTION_ALGORITHM
        ),
        "WORKFLOW": Numbered(system_parts.WORKFLOW_STEPS),
        "OUTPUT DISCIPLINE": system_parts.OUTPUT_DISCIPLINE,
    }


def user_prompt() -> PromptNode:
    """Assemble the LIBERO user prompt tree."""
    return {
        "CELL": user_parts.CELL,
        "MODE": user_parts.MODE,
        "BEGIN": user_parts.BEGIN,
    }


__all__ = ["system_prompt", "user_prompt"]
