"""Select authenticated saved report cells, without recalculating measurements."""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError
from .rfam_batch_contracts import closed_object, finite_json_copy, is_text, query_strand_record_key, rfam_digest
from .rfam_batch_report_contracts import (
    RFAM_REPORT_METRIC_UNITS, validate_rfam_report_sheet,
    validate_rfam_report_calculation, validate_rfam_report_projection,
)


def project_rfam_batch_report_result(sheet, calculation, *, projection, artifact_bindings) -> dict:
    sheet = validate_rfam_report_sheet(sheet)
    calculation = validate_rfam_report_calculation(calculation, sheet=sheet)
    projection = validate_rfam_report_projection(projection)
    code = "rfam_projection_reference_conflict"
    bindings = finite_json_copy(artifact_bindings, code=code)
    closed_object(bindings, ("source_ref", "sheet_ref", "calculation_ref", "sheet_digest", "calculation_digest"), code=code)
    if (any(not is_text(bindings[k]) for k in ("source_ref", "sheet_ref", "calculation_ref"))
            or bindings["source_ref"] != sheet["capture"]["source_ref"]
            or bindings["sheet_digest"] != rfam_digest(sheet)
            or bindings["calculation_digest"] != rfam_digest(calculation)):
        raise ContractError(code)
    family = projection["family"]
    rows = calculation["hits" if family == "hit" else "query_strands"]
    keys = [row["hit_key"] if family == "hit" else query_strand_record_key(row["query_occurrence_key"], row["strand"]) for row in rows]
    if len(set(keys)) != len(keys):
        raise ContractError(code)
    selection = projection["rows"]
    if "record_keys" in selection:
        mapping = {key: index for index, key in enumerate(keys)}
        if any(key not in mapping for key in selection["record_keys"]):
            raise ContractError(code)
        selected = [mapping[key] for key in selection["record_keys"]]
    else:
        selected = range(selection["offset"], min(selection["offset"] + selection["limit"], len(rows)))
    result = []
    for index in selected:
        row = rows[index]
        measured, unavailable = [], []
        for metric in projection["metrics"]:
            if row[metric] is None:
                unavailable.append(dict(name=metric, reason=row["missing"][metric]))
            else:
                measured.append(dict(name=metric, value=row[metric], unit=RFAM_REPORT_METRIC_UNITS[metric]))
        result.append(dict(record_key=keys[index], query_occurrence_key=row["query_occurrence_key"],
            family_accession=row.get("family_accession"), model_name=row.get("model_name"),
            strand=row["strand"], measured=measured, unavailable=unavailable))
    return dict(version="rfam_selected_projection_v1", source_ref=bindings["source_ref"],
        sheet_ref=bindings["sheet_ref"], calculation_ref=bindings["calculation_ref"], family=family,
        selection=deepcopy(projection), available_row_count=len(rows), selected_row_count=len(result),
        more_rows=len(result) < len(rows), population_complete=calculation["population_complete"] if family == "hit"
            else all(row["population_complete"] for row in rows), rows=result)


__all__ = ["project_rfam_batch_report_result"]
