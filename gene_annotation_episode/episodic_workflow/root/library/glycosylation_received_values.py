"""Original glycosylation received values for supplied decision information."""
from __future__ import annotations
from .molecular_provenance_display import _molecular_failure_view
from .molecular_provenance_display import _molecular_provenance_role
from .molecular_provenance_display import _molecular_stored_view
from .decision_prompt_text import _rows
from .decision_prompt_text import _scalar
from .decision_prompt_text import _table


def _n_glycosylation_text(packet, number):
    return _glycosylation_text(packet, number)


def _glycosylation_text(packet, number):
    """Render retained glyco cells and qualifications without reading or calculating."""
    values, context = packet["values"], packet["values"]["context"]
    o_density = values["operation"] == "predict_o_glycosylation_hotspots"
    input_cell = context["input"]["input_ref"]
    associations = [input_cell["value"]] if input_cell["value_state"] == "stored_value" else []

    def subject_label(reference):
        if reference not in associations:
            associations.append(reference)
        return "Input association" if reference == input_cell["value"] else "Mapped subject " + str(associations.index(reference) + 1)

    def literal(value):
        if isinstance(value, (dict, list)):
            return "; ".join(name + "=" + shown for name, shown in _rows(value))
        return _scalar(value)

    selected, qualifications = [], []
    for row in values["rows"]:
        value = row["value"]
        if row["field"].endswith("source_intervals") and isinstance(value, list):
            shown = "; ".join(subject_label(segment["subject_ref"]) + " [" + str(segment["start"])
                + "," + str(segment["end"]) + ") " + segment["unit"] + " " + segment["strand"]
                for segment in value) if value else "empty array"
        else:
            shown = literal(value)
        selected_row = (literal(row["row_id"]), row["field"], shown, row["value_state"],
            row["unit"], row["population_id"], _molecular_provenance_role(row["source_ref"], packet), row["source_pointer"])
        if o_density:
            operands = literal([_molecular_stored_view(cell, packet) for cell in row["denominators"]])
            selected_row = (*selected_row[:6], operands, *selected_row[6:])
        selected.append(selected_row)
        for name, cell in row["scientific_qualifiers"]["states"].items():
            qualification = (literal(row["row_id"]), name, literal(cell["value"]), cell["value_state"])
            if qualification not in qualifications:
                qualifications.append(qualification)

    retained = [("component_status", context["component_status"])]
    for group in ("parameters", "input", "mapping"):
        retained.extend((group + "." + name, cell) for name, cell in context[group].items())
    retained.append(("completeness", context["completeness"]))
    facts = []
    for name, cell in retained:
        shown = ("supplied input association" if cell["value_state"] == "stored_value" else "null") if name == "input.input_ref" else literal(cell["value"])
        facts.append((name, shown, cell["value_state"], _molecular_provenance_role(cell["source_ref"], packet), cell["source_pointer"]))

    columns = ("Row identity", "Field", "Literal value", "Value state", "Unit", "Population", "Source role", "Source pointer")
    if o_density:
        columns = (*columns[:6], "Denominator operands", *columns[6:])
    interpretation = ("Interpretation: S/T density in reported windows under the selected heuristic. Candidate hotspots do not establish measured glycosylation, occupancy, calibrated probability or protein function."
        if o_density else "Interpretation: literal N-X-S/T motifs with X different from P. Occupancy and experimental glycosylation are unestablished.")
    parts = ["Selected molecular result " + str(number), "", interpretation, "",
        _table(("Result property", "Supplied value"), [("Callable result Source", packet["source_ref"]),
            ("Operation", values["operation"]), ("Values origin", values["source_kind"]),
            ("Original attempt association", values["original_attempt_association"])]), "",
        _table(("Retained file role", "State"), packet["file_states"].items()), "",
        _table(columns, selected), "",
        _table(("Retained property", "Literal value", "Value state", "Source role", "Source pointer"), facts), "",
        _table(("Row identity", "Original qualifier", "Literal value", "Value state"), qualifications)]

    metadata = context["native"]["metadata_occurrences"]
    native_rows = []
    if metadata["value_state"] == "stored_value":
        native_rows = [(item["kind"], literal(item["values"]), item["line_number"], item["native_line"])
            for item in metadata["value"]]
    parts.extend(["", "Original native header occurrences (order and duplicates retained)", "",
        _table(("Kind", "Literal reported values", "Log line", "Original native line"), native_rows)
            if metadata["value_state"] == "stored_value" else metadata["value_state"], "",
        "Selected native headers", "",
        _table(("Literal value", "Value state"), [(literal(context["native"]["selected_metadata"]["value"]),
            context["native"]["selected_metadata"]["value_state"])])])

    issue_rows = []
    if context["row_issues"] is None:
        issue_rows.append(("retained row issues", "unavailable", "null"))
    issue_groups = [("components", context["component_issues"]),
        *([] if context["row_issues"] is None else [("retained row " + str(row["row_ordinal"]), row["issues"])
            for row in context["row_issues"]])]
    for group, cell in issue_groups:
        if cell["value_state"] != "stored_value":
            issue_rows.append((group, cell["value_state"], "null"))
        else:
            issue_rows.extend((group, cell["value_state"], literal(issue)) for issue in cell["value"])
    parts.extend(["", "Original component and row issues", "",
        _table(("Population", "Value state", "Original issue"), issue_rows) if issue_rows else "Known empty issue arrays."])
    for title, failures in (("Result failures", packet["failures"]), ("Selected-value failures", values["failures"])):
        rendered_failures = []
        for issue in failures:
            shown = _molecular_failure_view(issue, packet)
            if shown.get("diagnostic_ref") is not None:
                shown.pop("diagnostic_ref")
                shown["diagnostic_role"] = "retained diagnostic association"
            rendered_failures.append((literal(shown),))
        parts.extend(["", title, "", _table(("Original failure",),
            rendered_failures) if failures else "[]"])
    return "\n".join(parts)


