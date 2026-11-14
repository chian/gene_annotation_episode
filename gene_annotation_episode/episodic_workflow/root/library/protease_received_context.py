"""Original protease received context for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from .molecular_provenance_display import _molecular_literal
from .molecular_provenance_display import _molecular_provenance_role
from .decision_prompt_text import _table


def _protease_context_text(packet):
    """Present retained global qualifications, including an empty row selection."""
    def members(value, path=""):
        if isinstance(value, Mapping) and value:
            for key, child in value.items():
                yield from members(child, path + "." + key if path else key)
        elif isinstance(value, (list, tuple)) and value:
            for index, child in enumerate(value):
                yield from members(child, path + "[" + str(index) + "]")
        else:
            yield path, value

    def cells(value, path=""):
        if "value_state" in value:
            yield path, value
        else:
            for key, child in value.items():
                if key != "schema":
                    yield from cells(child, path + "." + key if path else key)

    rows = []
    for field, cell in cells(packet["values"]["context"]):
        values = members(cell["value"]) if field in ("assay", "population") else (("", cell["value"]),)
        for member, literal in values:
            name = field + ("." + member if member else "")
            rows.append((name, _molecular_literal(literal), cell["value_state"],
                _molecular_provenance_role(cell["source_ref"], packet), cell["source_state"], cell["source_pointer"]))
    return "\n\n".join(["Retained protease assay and qualification context",
        _table(("Retained field/member", "Literal value", "Value state", "Source role", "Source state", "Source pointer"), rows)])


