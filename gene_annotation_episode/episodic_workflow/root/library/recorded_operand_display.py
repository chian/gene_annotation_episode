"""Original recorded operand display for supplied decision information."""
from __future__ import annotations



_EXECUTION_OPAQUE_PREFIXES = ("artifact_", "source_", "observation_", "reference_", "operation_",
    "episode_", "goal_", "input_", "scientific_invocation_", "progress_", "execution_")


def _execution_opaque_reference(value):
    if not isinstance(value, str):
        return False
    for prefix in _EXECUTION_OPAQUE_PREFIXES:
        if value.startswith(prefix):
            suffix = value[len(prefix):]
            return 24 <= len(suffix) <= 64 and all(character in "0123456789abcdef" for character in suffix)
    return False


