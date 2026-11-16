"""Original protein disorder received values for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from .recorded_operand_display import _execution_opaque_reference
from .decision_prompt_text import _rows
from .decision_prompt_text import _table


def _protein_disorder_text(packet, number):
    """Display stored disorder cells and context; qualify declared addresses only."""
    values = deepcopy(packet["values"])
    context = values["context"]
    subjects = []

    def subject(reference):
        if not _execution_opaque_reference(reference):
            return reference
        if reference not in subjects:
            subjects.append(reference)
        return "Supplied mapping subject " + str(subjects.index(reference) + 1)

    def spans(value):
        if not isinstance(value, list):
            return value
        return [{**row, "subject_ref": subject(row["subject_ref"])}
            if isinstance(row, Mapping) and set(row) == {"subject_ref", "start", "end", "unit", "strand"}
            else row for row in value]

    def mapping(value):
        if (not isinstance(value, Mapping) or set(value) != {"version", "units_per_symbol", "symbol_length", "path"}
                or value["version"] != "oriented_source_subject_path_v2"):
            return value
        return {**value, "path": spans(value["path"])}

    # These fields are declared provenance slots. An opaque caller value in a
    # different field, including a malformed supplied mapping, stays literal.
    reference = context["input"]["input_ref"]
    if _execution_opaque_reference(reference):
        context["input"]["input_ref"] = "Retained input provenance"
    context["input"]["input_mapping"] = mapping(context["input"]["input_mapping"])
    context["mapping"]["supplied"] = mapping(context["mapping"]["supplied"])
    values["data_identity"] = {key: value for key, value in values["data_identity"].items()
        if key not in {"sheet_canonical_sha256", "components_canonical_sha256"}}
    for row in values["rows"]:
        if row["field"] == "source_intervals":
            row["value"] = spans(row["value"])
        qualifiers = row["scientific_qualifiers"]
        if qualifiers.get("kind") == "residue" and qualifiers.get("value") is not None:
            cells = qualifiers["value"]["cells"]
            cells["source_intervals"] = spans(cells["source_intervals"])
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "predict_protein_disorder_regions")]),
        _table(("Retained field/member", "Literal value"),
            _rows({"selection": packet["selection"]["rows"], "values": values}))])


