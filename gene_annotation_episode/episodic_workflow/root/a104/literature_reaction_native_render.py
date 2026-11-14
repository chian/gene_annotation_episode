"""Display separately requested native reaction operands, without private keys."""
from collections.abc import Mapping


def is_row(row):
    return isinstance(row, Mapping) and row.get("evaluation_scope") == "native_reference_reaction_operands" and "observation_position" in row


def render_rows(parts, rows, records, *, section, table):
    records = records or {}
    def label(ref):
        row = records.get(ref, {})
        return row.get("label", row.get("name", "unknown")) if isinstance(row, Mapping) else "unknown"
    section(parts, "Requested native reaction observations", table(
        ("Observation", "Role", "Numerator", "Denominator", "Value", "Unit", "Source value", "Source unit",
         "Ratio form", "Measurement basis", "Transformation", "Reported count", "Count basis", "Independent n",
         "Uncertainty kind", "Uncertainty value"),
        ((row["observation_position"] + 1, row["operand_role"], label(row.get("numerator_ref")),
          label(row.get("denominator_ref")), row["value"], row["unit"], row["reported_value"], row["source_unit"],
          row["ratio_form"], row["measurement_basis"], row["transformation"], row["reported_count"],
          row["count_basis"], row["independent_n"], row["uncertainty_kind"], row["uncertainty_value"])
         for row in rows)))
    for index, row in enumerate(rows, 1):
        section(parts, "Native observation " + str(index) + " source meanings", table(
            ("Measurement", "Source operands", "Basis", "Repetition basis", "Uncertainty basis", "Numerator value", "Denominator value"),
            [(label(row["measurement_ref"]), "; ".join(label(ref) for ref in row["source_number_refs"]),
              "; ".join(label(ref) for ref in row["basis_refs"]), "; ".join(label(ref) for ref in row["count_basis_refs"]),
              "; ".join(label(ref) for ref in row["uncertainty_basis_refs"]), row["numerator_value"], row["denominator_value"])]))
