"""Explicit scientific-tool retrieval configuration."""
from collections.abc import Mapping
import json
from ..method_loop.durable import canonical


VERSION = "scientific_tool_retrieval_v1"
SEMANTIC = "semantic_fast_v1"
LITERAL = "literal_test_v1"


def configuration(value):
    """Validate explicit caller opt-in; None preserves the existing v3 binding."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("scientific_tool_retrieval_configuration_invalid")
    value = json.loads(canonical(value))
    expected = {"version", "mode"}
    if value.get("mode") == SEMANTIC:
        expected.add("model")
        model = value.get("model")
        if (not isinstance(model, dict) or set(model) != {"model", "reasoning_effort"}
                or any(not isinstance(item, str) or not item for item in model.values())):
            raise ValueError("scientific_tool_retrieval_configuration_invalid")
    if (set(value) != expected or value.get("version") != VERSION
            or value.get("mode") not in {SEMANTIC, LITERAL}):
        raise ValueError("scientific_tool_retrieval_configuration_invalid")
    return value

