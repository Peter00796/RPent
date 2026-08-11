"""LIBERO prompt bundle assembly."""

from __future__ import annotations

from robots.libero.prompts import system as system_parts
from robots.libero.prompts import user as user_parts
from rpent.context.prompt_utils import Numbered, PromptNode


def system_prompt(*, memory: bool = False, playbook: bool = False,
                  resident: bool = False) -> PromptNode:
    """Assemble the LIBERO system prompt tree.

    ``memory`` and ``playbook`` are CAPABILITIES, not profile names: main.py
    sets them iff the active sandbox actually exposes the corresponding
    roots, so the prompt and the enforcement can never disagree (a custom
    profile that exposes the library gets the library instructions, whatever
    it is called). ``resident`` levels the attempt regime the same way: the
    single-attempt blocks exist only when the run actually is single-attempt.
    """
    return {
        "ROLE AND EVALUATION": system_parts.role_and_evaluation(
            resident=resident),
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
        "WORKFLOW": Numbered(
            system_parts.workflow_steps(
                memory=memory, playbook=playbook, resident=resident)),
        "OUTPUT DISCIPLINE": system_parts.OUTPUT_DISCIPLINE,
    }


def user_prompt(*, memory: bool = False, playbook: bool = False,
                resident: bool = False) -> PromptNode:
    """Assemble the LIBERO user prompt tree (same capability flags as system;
    ``playbook`` and ``resident`` are accepted for signature parity — the
    resident brief replaces the user message in main.py)."""
    return {
        "CELL": user_parts.CELL,
        "MODE": user_parts.MODE,
        "BEGIN": user_parts.BEGIN_MEMORY if memory else user_parts.BEGIN,
    }


__all__ = ["system_prompt", "user_prompt"]
