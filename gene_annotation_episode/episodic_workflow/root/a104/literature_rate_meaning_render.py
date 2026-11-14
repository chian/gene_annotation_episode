"""Pure display of exact requested source-rate meanings, without expansion."""
from collections.abc import Mapping
from functools import lru_cache

from jsonschema import Draft202012Validator

from .communication import plain
from .domain import ContractError, canonical
from .literature_rate_meaning_delivery import MEANING_FIELDS, rate_source_meaning_cells_schema
from . import literature_rate_domains as domains


@lru_cache(maxsize=1)
def _validator():
    return Draft202012Validator(rate_source_meaning_cells_schema()["items"])


def is_row(value):
    return isinstance(value, Mapping) and _validator().is_valid(plain(value))


def base_rows(rows):
    result = []
    for row in rows:
        if not is_row(row):
            raise ContractError("literature_rate_meaning_display_contract_mismatch")
        result.append({key: plain(value) for key, value in row.items() if key not in MEANING_FIELDS})
    return result


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (list, tuple)) and rows and all(is_row(row) for row in rows):
                    yield from rows


def rows_from_values(values):
    """Find exact typed rows in retained lookup/history envelopes."""
    for value in values:
        if isinstance(value, Mapping):
            yield from rows_from_values(value.values())
        elif isinstance(value, (list, tuple)):
            if value and all(is_row(row) for row in value):
                yield from value
            else:
                yield from rows_from_values(value)


def own_rows(content, display_rows):
    display_rows = list(display_rows)
    matched = {(row["sheet_ref"], row["component"]) for row in domains.own_rows(content, base_rows(display_rows))}
    return [row for row in display_rows if (row["sheet_ref"], row["component"]) in matched]


def hidden_records(rows):
    return domains.hidden_records(base_rows(rows))


def render_meanings(parts, rows, *, section, table):
    rows = list(rows)
    base_rows(rows)
    if not rows:
        return
    first = rows[0]
    if any(row["sheet_ref"] != first["sheet_ref"] or
            canonical(row["comparison_intended_change"]) != canonical(first["comparison_intended_change"])
            for row in rows):
        raise ContractError("literature_rate_meaning_display_context_mismatch")
    def quote(witness):
        return witness["quote"] if witness is not None else "not recorded in selected inputs"
    section(parts, "Recorded intended experimental change", quote(first["comparison_intended_change"]))
    unique = {}
    for row in rows:
        for meaning in row["rate_meanings"]:
            role = meaning["arm"]
            if role in unique and canonical(unique[role]) != canonical(meaning):
                raise ContractError("literature_rate_meaning_display_context_mismatch")
            unique[role] = meaning
    section(parts, "Requested rate endpoint and unit meanings", table(
        ("Arm", "Endpoint", "Normalization / denominator", "Printed rate unit", "Canonical rate unit", "Conversion multiplier", "Unit unavailable reason"),
        ((role.capitalize(), quote(meaning["endpoint"]), quote(meaning["normalization"]),
          (unit or {}).get("raw_unit"), (unit or {}).get("canonical_unit"),
          (unit or {}).get("multiplier"), (unit or {}).get("unavailable_reason"))
         for role, meaning in unique.items() for unit in (meaning["rate_unit"],))))
    definitions = []
    for role, meaning in unique.items():
        unit = meaning["rate_unit"]
        defined = unit["source_defined_unit"] if unit is not None else None
        if defined is not None:
            definition = defined["definition"]
            definitions.append((role.capitalize(), quote(definition["bridge"]),
                quote(definition["clause"]), definition["amount"]["raw_number"],
                quote(definition["amount_unit"]), quote(definition["time_unit"]),
                quote(definition["endpoint_entity"]), quote(definition["definition_entity"])))
    if definitions:
        section(parts, "Source-defined rate units", table(
            ("Arm", "Source unit definition", "Selected endpoint clause", "Defined amount", "Amount unit", "Per time unit", "Endpoint entity", "Definition entity"), definitions))
    section(parts, "Meaning limits", "Only recorded witnesses and unit-conversion operands are shown. "
        "Missing selected meanings do not establish publication omissions. The intended-change witness "
        "does not establish a blank, isolated effect, molecular replacement or sufficiency.")


def render_received(parts, rows, records, *, section, table, comparison_number=None):
    rows = list(rows)
    if not rows:
        return
    domains.render_received(parts, base_rows(rows), records, section=section, table=table,
        comparison_number=comparison_number)
    render_meanings(parts, rows, section=section, table=table)


__all__ = ["is_row", "base_rows", "rows_from_reports", "rows_from_values", "own_rows", "hidden_records",
    "render_meanings", "render_received"]
