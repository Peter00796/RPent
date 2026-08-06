"""Planner built on LangChain's ``create_agent`` graph.

The tools are already native LangChain tools, so this planner adds only the
loop: build the chat model, assemble the middleware chain, hand the toolkit's
per-run context to the graph, and run until the model stops calling tools or the
turn budget is spent.

Why ``create_agent`` and not ``create_deep_agent``: the latter is the same graph
plus subagents, skills, memory, permissions and a virtual filesystem, and it
injects its own system prompt and tools. Those are real capabilities, but they
are *additional injections*, and an injection that is not declared cannot be
accounted for. They ship as individual middleware (``SubAgentMiddleware``,
``FilesystemMiddleware``, ``MemoryMiddleware``, …), so each one can be added as a
named, toggleable configuration entry and measured on its own. Starting here
keeps the injected surface equal to exactly the system prompt plus the declared
tools, which is also what makes a comparison against the other planners fair.
"""

from __future__ import annotations

import queue
from typing import Any

from rpent.dashboard.events import DashboardEventSink
from rpent.dashboard.interaction import DashboardInteractionPort
from rpent.planner.base import PlannerResult
from rpent.planner.middleware import TranscriptMiddleware
from rpent.tools.toolkit import Toolkit
from rpent.utils.logging import get_logger

logger = get_logger("deep_agent")

#: ``recursion_limit`` counts graph node executions, not model turns, and the
#: cost per turn grows with the middleware chain. Measured on langgraph 1.2.10:
#: the minimum viable limit is ``(3 + len(middleware)) * turns + 2`` — slope 4
#: with one middleware installed, 5 with two, linear thereafter. Since the real
#: turn budget is enforced by ``ModelCallLimitMiddleware``, this is only a
#: backstop against a graph that loops without calling the model, so it is set
#: to twice the measured requirement: a change in LangGraph's node layout then
#: cannot turn the backstop into a spurious failure, while a runaway graph is
#: still bounded.
_NODES_PER_TURN_BASE = 3
_RECURSION_SAFETY_FACTOR = 2
_RECURSION_HEADROOM = 20


def _recursion_limit(max_turns: int, n_middleware: int) -> int:
    """Return the graph-node backstop for ``max_turns`` model turns."""
    per_turn = _NODES_PER_TURN_BASE + n_middleware
    return (per_turn * max_turns + 2) * _RECURSION_SAFETY_FACTOR + _RECURSION_HEADROOM


class DeepAgentPlanner:
    """Planner that drives the toolkit through a LangChain agent graph."""

    def __init__(
        self,
        *,
        model: str,
        chat_model: Any,
        no_images: bool = False,
        dashboard_events: DashboardEventSink,
    ) -> None:
        """Store the already-constructed chat model.

        The model is built by :func:`build_chat_model` in ``build_planner``, not
        here, so an unusable ``--model`` fails before the env / VLA / SAM3
        servers spend minutes loading onto the GPU. ``model`` is kept only as the
        human-readable spec for logs.
        """
        self._model = model
        self._chat_model = chat_model
        self._no_images = no_images
        self._dashboard_events = dashboard_events

    def solve(
        self,
        *,
        system_prompt: str,
        user_message: str,
        toolkit: Toolkit,
        max_turns: int,
        input_queue: queue.Queue[str | None] | None = None,
        dashboard_interaction: DashboardInteractionPort | None = None,
    ) -> PlannerResult:
        """Run the agent graph until finish, a natural stop, or the turn budget."""
        if input_queue is not None:
            raise NotImplementedError(
                "the deepagents planner does not support --interactive yet; "
                "LangGraph steers through human-in-the-loop interrupts rather "
                "than a mid-run message queue, which is a separate change"
            )
        if dashboard_interaction is not None:
            raise NotImplementedError(
                "the deepagents planner does not support Dashboard interaction"
            )

        from langchain.agents import create_agent
        from langchain.agents.middleware import ModelCallLimitMiddleware

        recorder = TranscriptMiddleware(
            dashboard_events=self._dashboard_events,
            max_turns=max_turns,
        )
        context = toolkit.tool_context
        tools = toolkit.langchain_tools(no_images=self._no_images)
        logger.info(
            "deepagents planner: model=%s tools=%d max_turns=%d",
            self._model,
            len(tools),
            max_turns,
        )

        middleware = [
            ModelCallLimitMiddleware(run_limit=max_turns, exit_behavior="end"),
            recorder,
        ]
        agent = create_agent(
            model=self._chat_model,
            tools=tools,
            system_prompt=system_prompt or None,
            context_schema=type(context) if context is not None else None,
            middleware=middleware,
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        last_error: str | None = None
        invoke_kwargs: dict[str, Any] = {
            "config": {"recursion_limit": _recursion_limit(max_turns, len(middleware))}
        }
        if context is not None:
            invoke_kwargs["context"] = context

        try:
            agent.invoke({"messages": [("user", user_message)]}, **invoke_kwargs)
            if recorder.finish_result is not None:
                logger.info("FINISH called: %s", recorder.finish_result)
            elif recorder.turns >= max_turns:
                logger.info("reached max_turns=%d. Stopping.", max_turns)
            else:
                logger.info("model ended turn without a tool call. Stopping.")
        except Exception as e:  # noqa: BLE001 - surfaced via PlannerResult.error
            last_error = f"{type(e).__name__}: {e}"
            if _is_image_rejection(e) and not self._no_images:
                last_error += (
                    "\n\nThe model rejected image input — it is likely a "
                    "text-only model (no vision support). Re-run with "
                    "--no-images: RPent will then keep every visual "
                    "observation as a file-path text notice instead of "
                    "sending image bytes."
                )
            logger.error("agent run failed: %s", last_error)

        messages.extend(recorder.messages)
        return PlannerResult(
            finish_result=recorder.finish_result,
            messages=messages,
            stats=recorder.stats(),
            error=last_error,
        )

def build_chat_model(
    model: str,
    *,
    base_url: str | None = None,
    max_tokens: int = 8192,
) -> Any:
    """Build the chat model from a ``provider:id`` spec and the CLI overrides.

    Called from ``build_planner`` so an unusable model spec raises before the
    env / VLA / SAM3 servers boot — the same failure timing the pydantic-ai
    planner gets from ``infer_model``.

    ``--model`` uses the same ``provider:id`` form that planner takes
    (``anthropic:claude-opus-4-8``), which is also what ``init_chat_model``
    expects, so the command line is unchanged. API keys keep coming from the
    provider's own environment variables; ``--base-url`` overrides the endpoint.
    """
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"max_tokens": max_tokens}
    if base_url:
        kwargs["base_url"] = base_url
    return init_chat_model(model, **kwargs)


def _is_image_rejection(e: Exception) -> bool:
    """True when the provider returned a 4xx complaining about image input."""
    text = str(e).lower()
    if "image" not in text:
        return False
    return any(code in text for code in ("400", "422", "bad request", "unsupported"))
