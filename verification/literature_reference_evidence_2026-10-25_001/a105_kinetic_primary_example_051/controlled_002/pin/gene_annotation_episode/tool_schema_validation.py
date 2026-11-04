"""Content-keyed validation of tool input schemas during library construction.

Only successful JSON Schema syntax checks are cached. The catalog, resource
owner, invocation route, instructions and actual arguments are checked by their
existing consumers on every use; none of those results are cached here.
"""
from functools import lru_cache
import json

from jsonschema import Draft202012Validator
from method_loop.durable import canonical


@lru_cache(maxsize=512)
def _check_serialized_schema(serialized: str) -> None:
    Draft202012Validator.check_schema(json.loads(serialized))


def check_tool_schema(schema: dict) -> None:
    """Validate the complete current schema, reusing an identical prior check.

    Serializing before lookup makes edits to nested dictionaries a new key.
    Failed checks are not cached, and callers receive the original SchemaError.
    """
    _check_serialized_schema(canonical(schema))
