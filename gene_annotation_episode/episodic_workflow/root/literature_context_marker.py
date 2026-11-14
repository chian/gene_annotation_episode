"""Recognize the original literature-context marker without importing its renderer."""

from collections.abc import Mapping

VERSION = "literature_experimental_task_v1"


def is_literature_experimental_context(state):
    marker = state.get("literature_experimental_work") if isinstance(state, Mapping) else None
    return isinstance(marker, Mapping) and marker.get("version") == VERSION
