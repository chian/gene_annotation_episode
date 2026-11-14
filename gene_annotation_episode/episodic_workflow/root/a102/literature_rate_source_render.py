"""Scientific display of the existing native source-rate return, without IO.

The host supplies only owned/admitted rows and possessed meaning records.
Rendering does not read a source, infer a missing meaning, or recompute a cell.
"""
from collections.abc import Mapping
from functools import lru_cache

from jsonschema import Draft202012Validator


MEANING_FIELDS = {
    "assayed_subject_ref": "reference", "experiment_ref": "reference",
    "reference_condition_ref": "context", "test_condition_ref": "context",
    "endpoint_ref": "term", "normalization_ref": "term",
    **{role + "_" + name + "_ref": "reference"
       for role in ("reference", "test")
       for name in ("subject", "construct", "preparation")},
}

_CELL_FIELDS = ("value", "unit", "status", "origin", "unavailable_reason",
                "conditional_on", "approximate", "threshold", "bound")
_COMPONENTS = {
    "reference_rate": "Reference rate",
    "test_rate": "Test rate",
    "rate_difference": "Reference − test rate",
    "retained_fraction": "Test / reference rate",
    "fractional_decrease": "1 − test / reference rate",
    "reference_mean_se": "Reference mean standard error",
    "test_mean_se": "Test mean standard error",
    "difference_se": "Difference standard error",
    "signed_profile_log_ratio": "Signed profile log ratio",
    "source_signed_index": "Proposed signed source index",
}
_BOUNDS = {"none": "none", "lt": "<", "le": "≤", "gt": ">", "ge": "≥"}
_CONDITIONS = {
    "independent_normal_groups": "independent normal groups",
    "independent_groups": "independent groups",
}


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@lru_cache(maxsize=1)
def _row_validator():
    # The exact existing closed contract identifies this return. The import is
    # lazy because the storage module uses the shared communication boundary.
    from .literature_rate_storage import rate_source_cells_schema
    return Draft202012Validator(rate_source_cells_schema()["items"])


def is_row(value):
    return isinstance(value, Mapping) and _row_validator().is_valid(_plain(value))


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (list, tuple)) and rows and all(is_row(row) for row in rows):
                    yield from rows


def own_rows(content, display_rows):
    """Match an actual own outcome with its authenticated projected view."""
    if not isinstance(content, Mapping) or not isinstance(content.get("cells"), Mapping):
        return []
    reference = content.get("sheet_ref")
    matching = [row for row in display_rows if row["sheet_ref"] == reference]
    if not matching:
        return []
    result = []
    for row in matching:
        cell = content["cells"].get(row["component"])
        if cell is None:
            continue
        if not isinstance(cell, Mapping) or any(_plain(cell.get(key)) != _plain(row[key]) for key in _CELL_FIELDS):
            from .domain import ContractError
            raise ContractError("literature_rate_source_display_outcome_mismatch")
        result.append(row)
    return result


def hidden_records(rows):
    """Hide only handles displayed scientifically here, never a whole paper."""
    return {reference for row in rows
            for field in ("sheet_ref", "evidence_source_ref", *MEANING_FIELDS)
            if (reference := row[field]) is not None}


def render_received(parts, rows, records, *, section, table, comparison_number=None):
    """Render one exact comparison's requested rows and declared meanings."""
    rows = list(rows)
    if not rows:
        return
    unique = {}
    for row in rows:
        key = (row.get("sheet_ref"), row.get("component"))
        if key in unique and unique[key] != row:
            from .domain import ContractError
            raise ContractError("literature_rate_source_display_context_mismatch")
        unique.setdefault(key, row)
    rows = list(unique.values())
    first = rows[0]
    if (not all(is_row(row) for row in rows)
            or any(row["sheet_ref"] != first["sheet_ref"]
                   or any(row[field] != first[field] for field in MEANING_FIELDS)
                   for row in rows)):
        from .domain import ContractError
        raise ContractError("literature_rate_source_display_context_mismatch")

    def label(reference):
        if reference is None:
            return "unknown"
        record = records.get(reference)
        if not isinstance(record, Mapping):
            return "meaning retained for scoped access"
        return record.get("label", record.get("name", "meaning retained for scoped access"))

    title = "Native source-rate comparison" + (" " + str(comparison_number) if comparison_number is not None else "")
    section(parts, title, table(
        ("Experiment", "Measured endpoint", "Normalization", "Shared assayed subject"),
        [(label(first["experiment_ref"]), label(first["endpoint_ref"]),
          label(first["normalization_ref"]), label(first["assayed_subject_ref"]))]))
    section(parts, "Reference and test meanings", table(
        ("Arm", "Subject", "Construct", "Preparation", "Condition"),
        ((role.capitalize(), *(label(first[role + "_" + name + "_ref"])
          for name in ("subject", "construct", "preparation", "condition")))
         for role in ("reference", "test"))))
    section(parts, "Requested native source-rate components", table(
        ("Component", "Value", "Unit", "Status", "Bound", "Threshold",
         "Approximate", "Unavailable reason", "Required statistical conditions", "Origin"),
        ((_COMPONENTS[row["component"]], row["value"], row["unit"], row["status"],
          _BOUNDS[row["bound"]], row["threshold"], row["approximate"],
          row["unavailable_reason"], "; ".join(_CONDITIONS[item] for item in row["conditional_on"]) or "none declared",
          row["origin"]) for row in rows)))


def render_own_result(parts, content, display_rows, records, *, section, table):
    rows = own_rows(content, display_rows)
    if not rows:
        return False
    render_received(parts, rows, records, section=section, table=table)
    return True


__all__ = ["MEANING_FIELDS", "is_row", "rows_from_reports", "own_rows", "hidden_records",
           "render_received", "render_own_result"]
