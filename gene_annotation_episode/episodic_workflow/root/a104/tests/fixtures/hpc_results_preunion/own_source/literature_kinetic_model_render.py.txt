"""Display selected saved kinetic model meanings without raw operand expansion."""
from collections.abc import Mapping

from .literature_kinetic_model_storage import VIEW, FORMULA_MEANINGS


def is_row(value):
    return isinstance(value, Mapping) and value.get("view") == VIEW and "component" in value


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (tuple, list)):
                    yield from (row for row in values if is_row(row))


def own_rows(content):
    if isinstance(content, Mapping) and content.get("view") == VIEW:
        return list(content.get("rows", ()))
    return []


def rows_from_values(value):
    """Select already recorded rows from own-history/context lookup results."""
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from rows_from_values(child)


def render_received(parts, rows, records, *, section, table, values):
    """Only selected cell values, conditional meanings and safe source labels."""
    if not rows:
        return
    # Reuse the existing native kinetic span-aware label masker. Model rows
    # carry the same actual source-bound metadata and masked uncertainty values.
    from .literature_experimental_prompt import _kinetic_received
    _kinetic_received(parts, rows, records)
    first = rows[0]
    section(parts, "Kinetic log model meanings", values({name: first[name] for name in (
        "variance_status", "observation_model", "log_basis", "model_origin")}))
    section(parts, "Requested conditional kinetic calculation definitions", table(("Component", "Meaning", "Conditions"),
        ((row["component"], FORMULA_MEANINGS[row["formula_code"]], ", ".join(row["conditional_on"])) for row in rows)))
    section(parts, "Kinetic model interpretation support", table(("Support", "Source meaning"),
        ((i, "exact retained source witness; scoped source access available") for i, _ in enumerate(first["model_support_refs"], 1))))


__all__ = ["is_row", "rows_from_reports", "own_rows", "rows_from_values", "render_received"]
