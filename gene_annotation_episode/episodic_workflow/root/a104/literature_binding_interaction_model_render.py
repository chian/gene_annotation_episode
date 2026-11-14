"""Render admitted interaction model cells with span-aware operand masking."""
from collections.abc import Mapping
from copy import deepcopy

from .literature_binding_interaction_model_storage import VIEW, FORMULA_MEANINGS
from . import literature_binding_interaction_render as native


def is_row(value):
    return isinstance(value, Mapping) and value.get("view") == VIEW and "component" in value


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (tuple, list)):
                    yield from (row for row in values if is_row(row))


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from rows_from_values(child)


def own_rows(content):
    return list(content.get("rows", ())) if isinstance(content, Mapping) and content.get("view") == VIEW else []


def _masked(rows):
    result = deepcopy(list(rows))
    for row in result:
        for role in row["roles"].values():
            role["numeric_locations"].extend(row["model_support_locations"])
    return result


def hidden_records(rows, records):
    return native.hidden_records([{"model_cells": _masked(rows)}], records)


def hidden_results(value, records):
    """Keep empty own subsets from expanding operands via generic labels."""
    hidden = set()
    if isinstance(value, Mapping):
        if value.get("view") == VIEW:
            mask = value.get("operand_mask", {})
            locations = mask.get("locations", ())
            hidden.update(mask.get("reference_refs", ()))
            hidden.update(ref for ref, record in records.items() if native.overlaps_numbers(record, locations))
        for child in value.values():
            hidden.update(hidden_results(child, records))
    elif isinstance(value, (tuple, list)):
        for child in value:
            hidden.update(hidden_results(child, records))
    return hidden


def render_received(parts, rows, records, *, section, table, values):
    if not rows:
        return
    native.render_received(parts, _masked(rows), records, section=section, table=table, values=values)
    first = rows[0]
    section(parts, "Binding interaction model meanings", values({k: first[k] for k in (
        "contrast_meaning", "variance_status", "distribution", "log_basis", "reporting_event", "source_kind", "qualifications")}))
    section(parts, "Requested conditional interaction calculation definitions", table(("Component", "Meaning"),
        ((row["component"], FORMULA_MEANINGS[row["formula_code"]]) for row in rows)))
    section(parts, "Interaction model interpretation support",
        "Exact source support is retained for scoped access. Custody does not establish model applicability or independence. "
        "The received packet supplies covariance; its scientific origin requires source interpretation.")


__all__ = ["is_row", "rows_from_reports", "rows_from_values", "own_rows", "hidden_records", "hidden_results", "render_received"]
