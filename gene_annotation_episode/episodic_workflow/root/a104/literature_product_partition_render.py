"""Render only exact admitted partition rows; never load a complete child sheet."""
from collections.abc import Mapping
from functools import lru_cache

from jsonschema import Draft202012Validator

from .communication import plain
from .domain import ContractError
from .literature_product_partition_storage import product_partition_cells_schema, binding_references
from .literature_product_partition_calculations import COMPONENTS
from .literature_product_partition_inputs import MEANINGS


@lru_cache(maxsize=1)
def _validator():
    return Draft202012Validator(product_partition_cells_schema()["items"])


def is_row(value):
    return (isinstance(value, Mapping) and value.get("evaluation_scope") == "reported_selected_product_partition"
        and isinstance(value.get("component"), str) and value["component"] in COMPONENTS
        and _validator().is_valid(plain(value)))


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values(): yield from rows_from_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value: yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for value in report.values():
                if isinstance(value, (list, tuple)) and value and all(is_row(row) for row in value):
                    yield from value


def hidden_records(rows):
    """Dedicated tables render these exact meanings without host identities."""
    return set(binding_references(list(rows)))


def render_received(parts, rows, records=None, *, section, table):
    rows = list(rows)
    if any(not is_row(row) for row in rows):
        raise ContractError("literature_product_partition_display_contract_mismatch")
    if not rows:
        return
    records = records or {}
    def label(ref):
        record = records.get(ref)
        return record.get("label", "unknown") if isinstance(record, Mapping) else "not received or withheld"
    def meaning(quantity, name):
        status = quantity["meaning_status"][name]
        return label(quantity[name + "_ref"]) if status == "selected" else status.replace("_", " ")
    section(parts, "Requested product partition components", table(
        ("Component", "Value", "Unit", "Status", "Origin", "Bound threshold", "Bound", "Approximate", "Out of reported fraction range", "Unavailable reason"),
        ((row["component"], row["value"], row["unit"], row["status"], row["origin"], row["threshold"], row["bound"],
          row["approximate"], row["outside_reported_fraction_range"], row["unavailable_reason"]) for row in rows)))
    for row in rows:
        section(parts, "Recorded partition experiment", label(row["experiment_ref"]) if row["experiment_status"] == "selected"
            else row["experiment_status"].replace("_", " "))
        section(parts, row["component"] + " scientific meanings", table(
            ("Fraction role", "Scientific aspect", "Recorded source meaning"),
            ((q["role"], name.replace("_", " "), meaning(q, name))
             for q in row["quantities"] for name in MEANINGS)))
        section(parts, "Fraction interpretation qualifications", table(
            ("Fraction role", "Basis", "Endpoint stage", "Source qualification"),
            ((q["role"], q["basis"], q["stage"], q["qualification"]) for q in row["quantities"])))
        section(parts, "Selected fraction relationships", table(
            ("Same preparation", "Same endpoint", "Shared denominator"),
            [(row["relationships"]["same_preparation"], row["relationships"]["same_endpoint"], row["relationships"]["shared_denominator"])]))
        if row["evidence"]:
            section(parts, "Requested partition qualifications", table(
                ("Evidence role", "Recorded passage", "Availability"),
                ((e["role"], label(e["witness_ref"]), e["availability"]) for e in row["evidence"])))
    section(parts, "Partition interpretation limits", "Selected-fraction closure is not independent mass balance. "
        "Composition is not rate, specificity or molecular attribution. These dependent transforms add no independent replication. "
        "Numerical uncertainty propagation is not implemented in this route.")


__all__ = ["is_row", "rows_from_values", "rows_from_reports", "hidden_records", "render_received"]
