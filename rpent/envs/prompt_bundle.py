"""Prompt bundle dataclass for env-contributed LLM prompts.

Lives in :mod:`rpent.envs` so each env's
``prompt_bundle.py`` (e.g. :mod:`robots.libero.prompt_bundle`)
can import it without depending on the RPC transport layer.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rpent.context.prompt_utils import PromptNode, format_prompt

PromptFactory = Callable[..., PromptNode]

@dataclass(frozen=True)
class PromptBundle:
    """Python-defined prompt factories for one environment."""

    system: PromptFactory
    user: PromptFactory

    def render(
        self,
        variant: str,
        *,
        variables: Mapping[str, object] | None = None,
        **factory_kwargs: object,
    ) -> str:
        """Render one prompt variant (``"system"`` or ``"user"``).

        ``factory_kwargs`` pass through to the env's prompt factory — e.g.
        ``memory=True`` when the run's sandbox exposes the memory library, so
        the prompt tree can vary with the run's actual capabilities.
        """
        prompt = getattr(self, variant)(**factory_kwargs)
        return format_prompt(prompt, variables=variables)

