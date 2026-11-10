"""Release model-process and prompt memory between serial scientific decisions.

This changes local process lifetime only. The same model configuration and
complete durable scientific history remain in use. There is no research timer,
turn limit, token limit or usage stopping rule.
"""
from __future__ import annotations

import ctypes
import gc
from .providers import ModelConnection, _SessionConnection


def release_unused_memory():
    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
    except (AttributeError, OSError):
        return
    trim(0)


class _OneDecisionSession(_SessionConnection):
    def _presentation(self, *args, **kwargs):
        result = super()._presentation(*args, **kwargs)
        # This worker is retired after the decision. Its validated state is
        # already persisted by the owning runtime; keep only rendered input
        # while awaiting the model, rather than a second large schema graph.
        self.scientific_prompt_states.clear()
        release_unused_memory()
        return result


class SerialModelConnection(ModelConnection):
    """The standard call-scoped provider lifecycle with early prompt-memory release."""
    session_type = _OneDecisionSession

    async def _complete_serial(self, episode_id, role, instructions, context, output_schema):
        release_unused_memory()
        try:
            return await super()._complete_serial(
                episode_id, role, instructions, context, output_schema)
        finally:
            release_unused_memory()
