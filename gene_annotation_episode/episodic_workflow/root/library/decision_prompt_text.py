"""Original decision prompt text for supplied decision information."""
from __future__ import annotations
from ..decision_context import INSTRUCTIONS
from collections.abc import Mapping
from ..decision_context import TEXT_INSTRUCTIONS


def text_instructions(instructions):
    """Replace only the existing exchange protocol's JSON-reading directions."""
    return instructions.replace(INSTRUCTIONS, TEXT_INSTRUCTIONS).replace(
        "After its decision_lookup_result arrives", "After the requested information arrives")


def _scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _cell(value):
    return _scalar(value).replace("|", "\\|").replace("\n", "<br>")


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "None supplied."
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)])


def _rows(value, path=""):
    """Exact finite values, with paths retaining arbitrary caller field names."""
    if isinstance(value, Mapping):
        if not value:
            yield path or "value", "empty object"
        for name, child in value.items():
            yield from _rows(child, f"{path}.{name}" if path else name)
    elif isinstance(value, (list, tuple)):
        if not value:
            yield path or "value", "empty array"
        for index, child in enumerate(value):
            yield from _rows(child, f"{path}[{index}]")
    else:
        yield path or "value", _scalar(value)


def _section(parts, title, body):
    if body is not None:
        parts.extend(["", title, "", body])


def _pick(value, names):
    return {name: value[name] for name in names if name in value}


